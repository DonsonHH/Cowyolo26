#include "native_runtime.cpp"
extern "C" {
// All preparation, halo gathering, headers and output reconstruction remain
// inside inference timing. Queue packets retain the accepted tile arithmetic.
int pack_queue(const int8_t* x,const int32_t* bias,const int8_t* weights,
               const uint32_t* multiplier,const uint32_t* shifts,const uint8_t* lut,
               const int32_t* shape,const int32_t* blocks,int block_count,
               uint32_t* output,uint64_t capacity_words,uint32_t* descriptions) {
    int ci=shape[0],h=shape[1],w=shape[2],k=shape[3],stride=shape[4],pad=shape[5];
    int zp=shape[6],wzp=shape[7],ozp=shape[8],mode=shape[9],layer=shape[11];
    if(mode!=1&&mode!=2)return -20;
    int oh=(h+2*pad-k)/stride+1,ow=(w+2*pad-k)/stride+1;
    struct Tile {int yy,xx,hh,ww,hi,wi;size_t offset;};
    std::vector<Tile> tiles;size_t activation_bytes=0;
    for(int yy=0;yy<oh;yy+=16)for(int xx=0;xx<ow;xx+=16) {
        int hh=oh-yy<16?oh-yy:16,ww=ow-xx<16?ow-xx:16,hi=(hh-1)*stride+k,wi=(ww-1)*stride+k;
        tiles.push_back({yy,xx,hh,ww,hi,wi,activation_bytes});activation_bytes+=size_t((ci+7)&~7)*hi*wi;
    }
    bool prepare=block_count>1;
    if(prepare){
        activation_workspace.resize(activation_bytes);
        for(const auto& t:tiles){
            uint8_t* dst=activation_workspace.data()+t.offset;
            for(int chunk=0;chunk<ci;chunk+=32){int active=ci-chunk<32?ci-chunk:32;dst=gather_activation(x,ci,h,w,chunk,active,t.hi,t.wi,t.yy,t.xx,stride,pad,zp,dst);}
        }
    }
    uint64_t used=0,rx_offset=0;int command=0,total_commands=block_count*int(tiles.size());
    for(int block=0;block<block_count;block++){
        int oc=blocks[3*block],co=blocks[3*block+1],offset=blocks[3*block+2];
        for(size_t ti=0;ti<tiles.size();ti++){
            const auto& t=tiles[ti];int reuse=ti!=0;
            uint64_t payload=co*3+(mode==2?64:0);
            for(int chunk=0;chunk<ci;chunk+=32){int active=ci-chunk<32?ci-chunk:32,cip=(active+7)&~7;payload+=uint64_t(cip)*t.hi*t.wi/4;if(!reuse)payload+=uint64_t((co+7)&~7)*cip*k*k/4;}
            if(used+19+payload>capacity_words||payload>200000)return -21;
            uint32_t* header=output+used;header[0]=0x51434F34;header[1]=command==total_commands-1;
            uint32_t cfg[17]={uint32_t(ci),uint32_t(co),uint32_t(t.hi),uint32_t(t.wi),uint32_t(t.hh),uint32_t(t.ww),uint32_t(k),uint32_t(stride),uint32_t(zp&255),uint32_t(wzp&255),uint32_t(payload),uint32_t(pad),uint32_t(ozp&255),uint32_t(mode),1,uint32_t(reuse),uint32_t(((layer+1)<<8)|(oc/32))};
            std::memcpy(header+2,cfg,sizeof(cfg));uint32_t* packet=header+19;
            int words;
            if(prepare){
                uint8_t* dst=reinterpret_cast<uint8_t*>(packet);
                std::memcpy(dst,bias+oc,co*4);dst+=co*4;std::memcpy(dst,multiplier+oc,co*4);dst+=co*4;std::memcpy(dst,shifts+oc,co*4);dst+=co*4;
                if(mode==2){std::memcpy(dst,lut,256);dst+=256;}
                const uint8_t* src=activation_workspace.data()+t.offset;const int8_t* wt=weights+offset;
                for(int chunk=0;chunk<ci;chunk+=32){int active=ci-chunk<32?ci-chunk:32,cip=(active+7)&~7,wb=((co+7)&~7)*cip*k*k,ab=cip*t.hi*t.wi;
                    if(!reuse){std::memcpy(dst,wt,wb);dst+=wb;}wt+=wb;std::memcpy(dst,src,ab);dst+=ab;src+=ab;}
                words=int(dst-reinterpret_cast<uint8_t*>(packet))/4;
            }else words=pack_tile_cached(x,ci,h,w,co,t.hh,t.ww,t.yy,t.xx,k,stride,pad,zp,bias+oc,weights+offset,packet,multiplier+oc,shifts+oc,lut,mode,reuse);
            if(uint64_t(words)!=payload)return -22;
            uint32_t* desc=descriptions+command*7;desc[0]=oc;desc[1]=t.yy;desc[2]=t.xx;desc[3]=co;desc[4]=t.hh;desc[5]=t.ww;desc[6]=rx_offset;
            rx_offset+=(co*t.hh*t.ww+3)/4;used+=19+payload;command++;
        }
    }
    if(used>=2097152)return -23;
    return int(used);
}
void unpack_queue(const uint32_t* input,int8_t* output,int h,int w,const uint32_t* descriptions,int count){
    for(int i=0;i<count;i++){const uint32_t* d=descriptions+i*7;unpack_i8(reinterpret_cast<const int8_t*>(input+d[6]),output,h,w,d[0],d[1],d[2],d[3],d[4],d[5]);}
}
int wait_queue(volatile uint32_t* dma,volatile uint32_t* core,uint32_t* counts,uint32_t* states){
    double start=monotonic_seconds();
    while(true){uint32_t tx=dma[1],rx=dma[13],st=core[0];states[0]=tx;states[1]=rx;states[2]=st;
        if((tx|rx)&0x770)return -1;
        if((tx&2)&&(rx&2)&&(st&2))break;
        if(monotonic_seconds()-start>10)return -2;
    }
    if(states[2]&8)return -3;
    for(int i=0;i<9;i++)counts[i]=core[16+i];counts[9]=core[26];counts[10]=core[27];
    __sync_synchronize();return 0;
}
}
#include "graph_executor.cpp"
