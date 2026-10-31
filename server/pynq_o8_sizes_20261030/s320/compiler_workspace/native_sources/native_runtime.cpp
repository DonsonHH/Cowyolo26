#include <cstdint>
#include <cstring>
#include <cmath>
#include <ctime>
#include <vector>
#ifdef __ARM_NEON
#include <arm_neon.h>
#endif
static bool use_neon_layout=true;
static bool parallel_elementwise=false;
static bool prepack_enabled=false;
static std::vector<uint8_t> activation_workspace;
#ifdef __ARM_NEON
static void transpose8(uint8x8_t r[8]) {
    uint8x8x2_t a0=vtrn_u8(r[0],r[1]),a1=vtrn_u8(r[2],r[3]),a2=vtrn_u8(r[4],r[5]),a3=vtrn_u8(r[6],r[7]);
    uint16x4x2_t b0=vtrn_u16(vreinterpret_u16_u8(a0.val[0]),vreinterpret_u16_u8(a1.val[0]));
    uint16x4x2_t b1=vtrn_u16(vreinterpret_u16_u8(a0.val[1]),vreinterpret_u16_u8(a1.val[1]));
    uint16x4x2_t b2=vtrn_u16(vreinterpret_u16_u8(a2.val[0]),vreinterpret_u16_u8(a3.val[0]));
    uint16x4x2_t b3=vtrn_u16(vreinterpret_u16_u8(a2.val[1]),vreinterpret_u16_u8(a3.val[1]));
    uint32x2x2_t c0=vtrn_u32(vreinterpret_u32_u16(b0.val[0]),vreinterpret_u32_u16(b2.val[0]));
    uint32x2x2_t c1=vtrn_u32(vreinterpret_u32_u16(b1.val[0]),vreinterpret_u32_u16(b3.val[0]));
    uint32x2x2_t c2=vtrn_u32(vreinterpret_u32_u16(b0.val[1]),vreinterpret_u32_u16(b2.val[1]));
    uint32x2x2_t c3=vtrn_u32(vreinterpret_u32_u16(b1.val[1]),vreinterpret_u32_u16(b3.val[1]));
    r[0]=vreinterpret_u8_u32(c0.val[0]);r[1]=vreinterpret_u8_u32(c1.val[0]);
    r[2]=vreinterpret_u8_u32(c2.val[0]);r[3]=vreinterpret_u8_u32(c3.val[0]);
    r[4]=vreinterpret_u8_u32(c0.val[1]);r[5]=vreinterpret_u8_u32(c1.val[1]);
    r[6]=vreinterpret_u8_u32(c2.val[1]);r[7]=vreinterpret_u8_u32(c3.val[1]);
}
#endif
static uint8_t* gather_activation(const int8_t* x,int ci,int h,int w,int chunk,int actual,int hi,int wi,
                                 int oy,int ox,int stride,int padding,int zp,uint8_t* dst) {
    int cip=(actual+7)&~7;
    for(int group=0;group<cip;group+=8) for(int yy=0;yy<hi;yy++) {
        int sy=oy*stride-padding+yy,xx=0;
        while(xx<wi) {
            int sx=ox*stride-padding+xx;
#ifdef __ARM_NEON
            if(use_neon_layout && group+7<actual && sy>=0 && sy<h && sx>=0 && sx+7<w && xx+8<=wi) {
                uint8x8_t rows[8];
                for(int lane=0;lane<8;lane++)rows[lane]=vld1_u8(reinterpret_cast<const uint8_t*>(x+(chunk+group+lane)*h*w+sy*w+sx));
                transpose8(rows);for(int j=0;j<8;j++)vst1_u8(dst+j*8,rows[j]);dst+=64;xx+=8;continue;
            }
#endif
            bool valid=sy>=0&&sy<h&&sx>=0&&sx<w;
            if(!use_neon_layout) {
                uint64_t vector=0;
                for(int lane=0;lane<8;lane++) {
                    uint8_t value=valid&&group+lane<actual?uint8_t(x[(chunk+group+lane)*h*w+sy*w+sx]):uint8_t(zp);
                    vector|=uint64_t(value)<<(lane*8);
                }
                std::memcpy(dst,&vector,8);
            } else for(int lane=0;lane<8;lane++)dst[lane]=valid&&group+lane<actual?uint8_t(x[(chunk+group+lane)*h*w+sy*w+sx]):uint8_t(zp);
            dst+=8;xx++;
        }
    }
    return dst;
}
extern "C" {
void set_activation_prepack(int enable) {prepack_enabled=enable!=0;}
void set_parallel_elementwise(int enable) {parallel_elementwise=enable!=0;}
void set_neon_layout(int enable) {use_neon_layout=enable!=0;}
int wait_done(volatile uint32_t* dma,volatile uint32_t* core,uint32_t* counts,uint32_t* states);
int submit_dma(volatile uint32_t* dma,volatile uint32_t* core,uint32_t tx_addr,uint32_t rx_addr,
               uint32_t tx_bytes,uint32_t rx_bytes,int first) {
    if(!(dma[0]&1)||!(dma[12]&1)||((dma[1]|dma[13])&0x771))return -3;
    if(!first&&(!(dma[1]&2)||!(dma[13]&2)))return -4;
    if((tx_addr|rx_addr|tx_bytes|rx_bytes)&3 || tx_bytes==0 || rx_bytes==0 || tx_bytes>=8388608 || rx_bytes>=8388608)return -5;
    // Same Simple-Mode register/cache/lifetime contract as the PYNQ driver.
    dma[18]=rx_addr;dma[19]=0;__sync_synchronize();dma[22]=rx_bytes;
    __sync_synchronize();core[0]=1;
    dma[6]=tx_addr;dma[7]=0;__sync_synchronize();dma[10]=tx_bytes;
    __sync_synchronize();return 0;
}
// Offline blocked weights are copied verbatim. Only the dynamic activation halo
// is gathered at runtime, using compiled loops, including exact zero-point fill.
int pack_tile(const int8_t* x,int ci,int h,int w,int co,int oh,int ow,int oy,int ox,
              int k,int stride,int padding,int zp,const int32_t* bias,
              const int8_t* packed_weights,uint32_t* output) {
    uint8_t* dst=reinterpret_cast<uint8_t*>(output);
    std::memcpy(dst,bias,co*4);dst+=co*4;
    int cop=(co+7)&~7,hi=(oh-1)*stride+k,wi=(ow-1)*stride+k;
    for(int chunk=0;chunk<ci;chunk+=32) {
        int actual=ci-chunk<32?ci-chunk:32,cip=(actual+7)&~7;
        int wb=cop*cip*k*k;std::memcpy(dst,packed_weights,wb);dst+=wb;packed_weights+=wb;
        dst=gather_activation(x,ci,h,w,chunk,actual,hi,wi,oy,ox,stride,padding,zp,dst);
    }
    return int(dst-reinterpret_cast<uint8_t*>(output))/4;
}
int pack_tile_quant(const int8_t* x,int ci,int h,int w,int co,int oh,int ow,int oy,int ox,
              int k,int stride,int padding,int zp,const int32_t* bias,
              const int8_t* packed_weights,uint32_t* output,const uint32_t* multiplier,
              const uint32_t* shifts,const uint8_t* lut,int mode) {
    int extra=mode?co*2+(mode==2?64:0):0;
    int words=pack_tile(x,ci,h,w,co,oh,ow,oy,ox,k,stride,padding,zp,bias,packed_weights,output+extra);
    std::memcpy(output,bias,co*4);
    if(mode){std::memcpy(output+co,multiplier,co*4);std::memcpy(output+co*2,shifts,co*4);}
    if(mode==2)std::memcpy(output+co*3,lut,256);
    return words+extra;
}
int pack_tile_cached(const int8_t* x,int ci,int h,int w,int co,int oh,int ow,int oy,int ox,
              int k,int stride,int padding,int zp,const int32_t* bias,
              const int8_t* packed_weights,uint32_t* output,const uint32_t* multiplier,
              const uint32_t* shifts,const uint8_t* lut,int mode,int reuse) {
    uint8_t* dst=reinterpret_cast<uint8_t*>(output);
    std::memcpy(dst,bias,co*4);dst+=co*4;
    if(mode) {std::memcpy(dst,multiplier,co*4);dst+=co*4;std::memcpy(dst,shifts,co*4);dst+=co*4;}
    if(mode==2) {std::memcpy(dst,lut,256);dst+=256;}
    int cop=(co+7)&~7,hi=(oh-1)*stride+k,wi=(ow-1)*stride+k;
    for(int chunk=0;chunk<ci;chunk+=32) {
        int actual=ci-chunk<32?ci-chunk:32,cip=(actual+7)&~7,wb=cop*cip*k*k;
        if(!reuse) {std::memcpy(dst,packed_weights,wb);dst+=wb;}
        packed_weights+=wb;
        dst=gather_activation(x,ci,h,w,chunk,actual,hi,wi,oy,ox,stride,padding,zp,dst);
    }
    return int(dst-reinterpret_cast<uint8_t*>(output))/4;
}
void unpack_i32(const int32_t* src,int32_t* dst,int fullh,int fullw,int oc,int oy,int ox,
                int co,int oh,int ow) {
    for(int group=0;group<co;group+=8) for(int yy=0;yy<oh;yy++) for(int xx=0;xx<ow;xx++)
        for(int lane=0;lane<8&&group+lane<co;lane++)
            dst[(oc+group+lane)*fullh*fullw+(oy+yy)*fullw+ox+xx]=*src++;
}
void unpack_i8(const int8_t* src,int8_t* dst,int fullh,int fullw,int oc,int oy,int ox,
                int co,int oh,int ow) {
    for(int group=0;group<co;group+=8) for(int yy=0;yy<oh;yy++) {
        int xx=0;
        while(xx<ow) {
#ifdef __ARM_NEON
            if(use_neon_layout&&group+7<co&&xx+8<=ow) {
                uint8x8_t rows[8];for(int j=0;j<8;j++)rows[j]=vld1_u8(reinterpret_cast<const uint8_t*>(src)+j*8);
                transpose8(rows);
                for(int lane=0;lane<8;lane++)vst1_u8(reinterpret_cast<uint8_t*>(dst+(oc+group+lane)*fullh*fullw+(oy+yy)*fullw+ox+xx),rows[lane]);
                src+=64;xx+=8;continue;
            }
#endif
            for(int lane=0;lane<8&&group+lane<co;lane++)dst[(oc+group+lane)*fullh*fullw+(oy+yy)*fullw+ox+xx]=*src++;
            xx++;
        }
    }
}
void configure_quant(volatile uint32_t* core,const uint32_t* extra) {
    for(int i=0;i<3;i++)core[32+i]=extra[i];__sync_synchronize();
}
void configure_cache(volatile uint32_t* core,const uint32_t* extra) {
    for(int i=0;i<5;i++)core[32+i]=extra[i];__sync_synchronize();
}
void configure_changed(volatile uint32_t* core,const uint32_t* cfg,const uint32_t* extra,uint32_t* previous) {
    for(int i=0;i<12;i++)if(cfg[i]!=previous[i]){core[4+i]=cfg[i];previous[i]=cfg[i];}
    for(int i=0;i<5;i++)if(extra[i]!=previous[12+i]){core[32+i]=extra[i];previous[12+i]=extra[i];}
    __sync_synchronize();
}
int wait_done_quant(volatile uint32_t* dma,volatile uint32_t* core,uint32_t* counts,uint32_t* states) {
    int code=wait_done(dma,core,counts,states);
    if(code==0){
        counts[9]=core[26];counts[10]=core[27];
        if(counts[6]*4!=dma[10] || counts[7]*4!=dma[22])return -6;
    }
    return code;
}
void configure(volatile uint32_t* registers,const uint32_t* config) {
    for(int i=0;i<12;i++) registers[4+i]=config[i];
    __sync_synchronize();
}
int wait_done(volatile uint32_t* dma,volatile uint32_t* core,uint32_t* counts,uint32_t* states) {
    timespec start,now;clock_gettime(CLOCK_MONOTONIC,&start);
    while(true) {
        uint32_t tx=dma[1],rx=dma[13],status=core[0];
        states[0]=tx;states[1]=rx;states[2]=status;
        if(((tx|rx)&0x770)||(status&8)) return -1;
        if((tx&2)&&(rx&2)&&(status&2))break;
        clock_gettime(CLOCK_MONOTONIC,&now);
        if(double(now.tv_sec-start.tv_sec)+(now.tv_nsec-start.tv_nsec)*1e-9>5)return -2;
    }
    for(int i=0;i<9;i++)counts[i]=core[16+i];
    __sync_synchronize();return 0;
}
typedef int (*cache_callback)(int words,int direction);
static double monotonic_seconds() {
    timespec value;clock_gettime(CLOCK_MONOTONIC,&value);
    return double(value.tv_sec)+value.tv_nsec*1e-9;
}
// One native call per Conv layer. Cache operations retain the exact PYNQ BO
// synchronization contract through a checked callback; no cache bypass.
int execute_layer(const int8_t* x,int8_t* output,const int32_t* bias,const int8_t* weights,
                  const uint32_t* multiplier,const uint32_t* shifts,const uint8_t* lut,
                  const int32_t* shape,const int32_t* blocks,int block_count,
                  uint32_t* tx,int8_t* rx,volatile uint32_t* dma,volatile uint32_t* core,
                  uint32_t tx_addr,uint32_t rx_addr,uint32_t* previous,int32_t* state,
                  cache_callback sync,uint32_t* trace,double* timing,double* diagnostic) {
    int ci=shape[0],h=shape[1],w=shape[2],k=shape[3],stride=shape[4],pad=shape[5];
    int zp=shape[6],wzp=shape[7],ozp=shape[8],mode=shape[9],overlap=shape[10],layer=shape[11];
    int oh=(h+2*pad-k)/stride+1,ow=(w+2*pad-k)/stride+1,command=0;
    struct Tile {int yy,xx,hh,ww,hi,wi;size_t offset;};
    std::vector<Tile> tiles;
    size_t activation_bytes=0;
    for(int yy=0;yy<oh;yy+=16)for(int xx=0;xx<ow;xx+=16) {
        int hh=oh-yy<16?oh-yy:16,ww=ow-xx<16?ow-xx:16;
        int hi=(hh-1)*stride+k,wi=(ww-1)*stride+k;
        tiles.push_back({yy,xx,hh,ww,hi,wi,activation_bytes});
        activation_bytes+=size_t((ci+7)&~7)*hi*wi;
    }
    bool prepare=prepack_enabled&&block_count>1;
    double prepare_start=monotonic_seconds();
    if(prepare) {
        activation_workspace.resize(activation_bytes);
        for(const auto& t:tiles) {
            uint8_t* dst=activation_workspace.data()+t.offset;
            for(int chunk=0;chunk<ci;chunk+=32) {
                int actual=ci-chunk<32?ci-chunk:32;
                dst=gather_activation(x,ci,h,w,chunk,actual,t.hi,t.wi,t.yy,t.xx,stride,pad,zp,dst);
            }
        }
    }
    timing[0]+=(monotonic_seconds()-prepare_start)*1000;
    for(int block=0;block<block_count;block++) {
        int oc=blocks[3*block],co=blocks[3*block+1],offset=blocks[3*block+2];
        for(const auto& tile:tiles) {
            int yy=tile.yy,xx=tile.xx,hh=tile.hh,ww=tile.ww;
            double tile_start=diagnostic?monotonic_seconds():0;
            double* detail=diagnostic?diagnostic+command*8:nullptr;
            int reuse=state[1]==layer&&state[2]==oc;
            int64_t predicted=co*4+(mode?co*8:0)+(mode==2?256:0);
            int hi=(hh-1)*stride+k,wi=(ww-1)*stride+k;
            for(int chunk=0;chunk<ci;chunk+=32) {
                int actual=ci-chunk<32?ci-chunk:32,cip=(actual+7)&~7;
                predicted+=int64_t(cip)*hi*wi;
                if(!reuse)predicted+=int64_t((co+7)&~7)*cip*k*k;
            }
            if(predicted>200000*4 || (co*hh*ww+3)/4>8192)return -10;
            double start=monotonic_seconds();
            int words;
            if(prepare) {
                uint8_t* dst=reinterpret_cast<uint8_t*>(tx);
                std::memcpy(dst,bias+oc,co*4);dst+=co*4;
                if(mode){std::memcpy(dst,multiplier+oc,co*4);dst+=co*4;std::memcpy(dst,shifts+oc,co*4);dst+=co*4;}
                if(mode==2){std::memcpy(dst,lut,256);dst+=256;}
                const uint8_t* src=activation_workspace.data()+tile.offset;
                const int8_t* wt=weights+offset;
                for(int chunk=0;chunk<ci;chunk+=32) {
                    int actual=ci-chunk<32?ci-chunk:32,cip=(actual+7)&~7;
                    int wb=((co+7)&~7)*cip*k*k,ab=cip*hi*wi;
                    if(!reuse){std::memcpy(dst,wt,wb);dst+=wb;}wt+=wb;
                    std::memcpy(dst,src,ab);dst+=ab;src+=ab;
                }
                words=int(dst-reinterpret_cast<uint8_t*>(tx))/4;
            } else words=pack_tile_cached(x,ci,h,w,co,hh,ww,yy,xx,k,stride,pad,zp,bias+oc,
                                      weights+offset,tx,multiplier+oc,shifts+oc,lut,mode,reuse);
            timing[0]+=(monotonic_seconds()-start)*1000;
            if(detail)detail[0]=(monotonic_seconds()-start)*1000;
            int outwords=(co*hh*ww+3)/4;
            if(words>200000||outwords>8192)return -10;
            uint32_t cfg[12]={uint32_t(ci),uint32_t(co),uint32_t((hh-1)*stride+k),uint32_t((ww-1)*stride+k),
                              uint32_t(hh),uint32_t(ww),uint32_t(k),uint32_t(stride),uint32_t(zp&255),
                              uint32_t(wzp&255),uint32_t(words),uint32_t(pad)};
            uint32_t extra[5]={uint32_t(ozp&255),uint32_t(mode),uint32_t(overlap),uint32_t(reuse),uint32_t(((layer+1)<<8)|(oc/32))};
            double mark=diagnostic?monotonic_seconds():0;
            configure_changed(core,cfg,extra,previous);
            if(detail)detail[1]=(monotonic_seconds()-mark)*1000;
            start=monotonic_seconds();
            mark=diagnostic?monotonic_seconds():0;
            if(sync(words,0))return -11;
            if(detail)detail[2]=(monotonic_seconds()-mark)*1000;
            mark=diagnostic?monotonic_seconds():0;
            int rc=submit_dma(dma,core,tx_addr,rx_addr,words*4,outwords*4,state[0]);
            if(detail)detail[3]=(monotonic_seconds()-mark)*1000;
            if(rc)return rc;
            state[0]=0;
            uint32_t counts[11],states[3];
            mark=diagnostic?monotonic_seconds():0;
            rc=wait_done_quant(dma,core,counts,states);
            if(detail)detail[4]=(monotonic_seconds()-mark)*1000;
            for(int i=0;i<3;i++)state[3+i]=states[i];
            if(rc)return rc;
            mark=diagnostic?monotonic_seconds():0;
            if(sync(outwords,1))return -12;
            if(detail)detail[5]=(monotonic_seconds()-mark)*1000;
            timing[1]+=(monotonic_seconds()-start)*1000;
            if(counts[6]!=uint32_t(words)||counts[7]!=uint32_t(outwords))return -13;
            state[1]=layer;state[2]=oc;
            start=monotonic_seconds();
            unpack_i8(rx,output,oh,ow,oc,yy,xx,co,hh,ww);
            timing[2]+=(monotonic_seconds()-start)*1000;
            if(detail){detail[6]=(monotonic_seconds()-start)*1000;detail[7]=(monotonic_seconds()-tile_start)*1000;}
            uint32_t* item=trace+command*15;
            for(int i=0;i<11;i++)item[i]=counts[i];
            item[11]=words*4;item[12]=outwords*4;item[13]=reuse;item[14]=oc;
            command++;
        }
    }
    return command;
}
static inline int round_even(float x) {
    #ifdef __arm__
    float bits;
    asm("vcvtr.s32.f32 %0, %1" : "=t"(bits) : "t"(x));
    int value;std::memcpy(&value,&bits,4);return value;
    #else
    return int(std::nearbyint(x));
    #endif
}
void quantize(const float* input,int8_t* output,int size,float scale,int zp) {
    #pragma omp parallel for schedule(static) num_threads(2) if(size>=65536)
    for(int i=0;i<size;i++) {
        float v=input[i]/scale;
        int q=v<=-128-zp?-128:v>=127-zp?127:round_even(v)+zp;
        output[i]=int8_t(q);
    }
}
void dequantize(const int8_t* input,float* output,int size,float scale,int zp) {
    int vectors=size/8;
    #pragma omp parallel for schedule(static) num_threads(2) if(size>=65536)
    for(int block=0;block<vectors;block++) {
        int i=block*8;
        #ifdef __ARM_NEON
        int16x8_t values=vmovl_s8(vld1_s8(input+i));
        int32x4_t low=vsubq_s32(vmovl_s16(vget_low_s16(values)),vdupq_n_s32(zp));
        int32x4_t high=vsubq_s32(vmovl_s16(vget_high_s16(values)),vdupq_n_s32(zp));
        vst1q_f32(output+i,vmulq_n_f32(vcvtq_f32_s32(low),scale));
        vst1q_f32(output+i+4,vmulq_n_f32(vcvtq_f32_s32(high),scale));
        #else
        for(int j=0;j<8;j++)output[i+j]=(int(input[i+j])-zp)*scale;
        #endif
    }
    for(int i=vectors*8;i<size;i++)output[i]=(int(input[i])-zp)*scale;
}
void lookup_int8(const int8_t* input,int8_t* output,int size,const int8_t* table) {
    #pragma omp parallel for schedule(static) num_threads(2) if(size>=65536)
    for(int i=0;i<size;i++)output[i]=table[uint8_t(input[i])];
}
// Separable same-padding odd-kernel max pool. Ordered selects retain the last
// equal operand, including signed zero; no approximate arithmetic is used.
static inline float ordered_max(float a,float b) {
    return std::isnan(b)||b>=a?b:a;
}
#ifdef __ARM_NEON
static inline float32x4_t ordered_max4(float32x4_t a,float32x4_t b) {
    uint32x4_t take=vorrq_u32(vcgeq_f32(b,a),vmvnq_u32(vceqq_f32(b,b)));
    return vbslq_f32(take,b,a);
}
#endif
void maxpool_float(const float* input,float* output,float* scratch,int channels,int h,int w,int k) {
    int pad=k/2;
    #pragma omp parallel for schedule(static) num_threads(2) if(channels>=64)
    for(int c=0;c<channels;c++) {
        int base=c*h*w;
        for(int y=0;y<h;y++) {
            int x=0;
            #ifdef __ARM_NEON
            for(;x+4<=w;x+=4) {
                float32x4_t maximum=vdupq_n_f32(-INFINITY);
                for(int dx=-pad;dx<=pad;dx++) {
                    int sx=x+dx;
                    if(sx>=0&&sx+3<w)maximum=ordered_max4(maximum,vld1q_f32(input+base+y*w+sx));
                    else {
                        float values[4];for(int lane=0;lane<4;lane++)values[lane]=(sx+lane>=0&&sx+lane<w)?input[base+y*w+sx+lane]:-INFINITY;
                        maximum=ordered_max4(maximum,vld1q_f32(values));
                    }
                }
                vst1q_f32(scratch+base+y*w+x,maximum);
            }
            #endif
            for(;x<w;x++) {
                float maximum=-INFINITY;
                for(int dx=-pad;dx<=pad;dx++)if(x+dx>=0&&x+dx<w)maximum=ordered_max(maximum,input[base+y*w+x+dx]);
                scratch[base+y*w+x]=maximum;
            }
        }
        for(int y=0;y<h;y++) {
            int x=0;
            #ifdef __ARM_NEON
            for(;x+4<=w;x+=4) {
                float32x4_t maximum=vdupq_n_f32(-INFINITY);
                for(int dy=-pad;dy<=pad;dy++)if(y+dy>=0&&y+dy<h)maximum=ordered_max4(maximum,vld1q_f32(scratch+base+(y+dy)*w+x));
                vst1q_f32(output+base+y*w+x,maximum);
            }
            #endif
            for(;x<w;x++) {
                float maximum=-INFINITY;
                for(int dy=-pad;dy<=pad;dy++)if(y+dy>=0&&y+dy<h)maximum=ordered_max(maximum,scratch[base+(y+dy)*w+x]);
                output[base+y*w+x]=maximum;
            }
        }
    }
}
void accumulator_float(const int32_t* input,float* output,int co,int spatial,const float* scale) {
    for(int channel=0;channel<co;channel++)for(int i=0;i<spatial;i++)
        output[channel*spatial+i]=float(input[channel*spatial+i])*scale[channel];
}
void lut_float(const int8_t* input,float* output,int size,const float* lut) {
    #pragma omp parallel for schedule(static) num_threads(2) if(parallel_elementwise&&size>=65536)
    for(int i=0;i<size;i++)output[i]=lut[uint8_t(input[i])];
}
void silu(const float* input,float* output,int size) {
    #pragma omp parallel for schedule(static) num_threads(2) if(parallel_elementwise&&size>=65536)
    for(int i=0;i<size;i++)output[i]=input[i]*(1.0f/(1.0f+std::exp(-input[i])));
}
void matmul(const float* a,const float* b,float* c,int m,int n,int k) {
    #ifdef __ARM_NEON
    #pragma omp parallel for schedule(static)
    for(int i=0;i<m;i+=4) {
        for(int j=0;j<n;j+=4) {
            if(i+3<m&&j+3<n) {
                float32x4_t s0=vdupq_n_f32(0),s1=s0,s2=s0,s3=s0;
                for(int l=0;l<k;l++) {
                    float32x4_t bb=vld1q_f32(b+l*n+j);
                    s0=vmlaq_n_f32(s0,bb,a[(i+0)*k+l]);s1=vmlaq_n_f32(s1,bb,a[(i+1)*k+l]);
                    s2=vmlaq_n_f32(s2,bb,a[(i+2)*k+l]);s3=vmlaq_n_f32(s3,bb,a[(i+3)*k+l]);
                }
                vst1q_f32(c+(i+0)*n+j,s0);vst1q_f32(c+(i+1)*n+j,s1);
                vst1q_f32(c+(i+2)*n+j,s2);vst1q_f32(c+(i+3)*n+j,s3);
            } else for(int ii=i;ii<m&&ii<i+4;ii++)for(int jj=j;jj<n&&jj<j+4;jj++) {
                float sum=0;for(int l=0;l<k;l++)sum+=a[ii*k+l]*b[l*n+jj];c[ii*n+jj]=sum;
            }
        }
    }
    #else
    for(int i=0;i<m;i++)for(int j=0;j<n;j++){float sum=0;for(int l=0;l<k;l++)sum+=a[i*k+l]*b[l*n+j];c[i*n+j]=sum;}
    #endif
}
}
