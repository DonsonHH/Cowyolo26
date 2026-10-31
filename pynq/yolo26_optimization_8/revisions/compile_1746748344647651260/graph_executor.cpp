// O8 independent static graph engine. No FPGA programming occurs in this file.
#include <algorithm>
#include <array>
#include <fstream>
#include <string>
#include <stdexcept>
#include <numeric>
#include <memory>
#include <map>
#include <cstdlib>
#ifndef _WIN32
#include <dlfcn.h>
#endif
namespace o7 {
using I=long long;
static std::string error;
static double now(){return monotonic_seconds()*1000.;}
static void check(bool b,const char* s){if(!b)throw std::runtime_error(s);}
static int bytes(int t){return t==1||t==6||t==12?4:t==7?8:1;}
// Reciprocal multiplication is accepted only away from a rounding boundary.
// At |code|<=512 its normal-FP32 error is <1e-4; ambiguous lanes use the
// original scalar division and ties-to-even instruction. Saturation is exact.
static void fast_quantize(const float*in,int8_t*out,int count,float scale,int zp){
#ifdef __ARM_NEON
 float inv=1.f/scale;if(!std::isfinite(inv)||scale<1e-30f){quantize(in,out,count,scale,zp);return;}
 int blocks=count/4;
 #pragma omp parallel for schedule(static) num_threads(2) if(count>=65536)
 for(int block=0;block<blocks;block++){int i=block*4;float32x4_t x=vld1q_f32(in+i);uint32x4_t finite=vcleq_f32(vabsq_f32(x),vdupq_n_f32(3.402823466e38f));x=vmulq_n_f32(x,inv);x=vmaxq_f32(vdupq_n_f32(-512),vminq_f32(vdupq_n_f32(512),x));float32x4_t ax=vabsq_f32(x),frac=vsubq_f32(ax,vcvtq_f32_s32(vcvtq_s32_f32(ax)));uint32x4_t near=vorrq_u32(vcltq_f32(vabsq_f32(vsubq_f32(frac,vdupq_n_f32(.5f))),vdupq_n_f32(.0002f)),vmvnq_u32(finite));uint32_t mask[4];vst1q_u32(mask,near);
  if(mask[0]|mask[1]|mask[2]|mask[3]){for(int j=0;j<4;j++){float v=in[i+j]/scale;out[i+j]=v<=-128-zp?-128:v>=127-zp?127:int8_t(round_even(v)+zp);}}
  else{int32x4_t q=vcvtq_s32_f32(vaddq_f32(ax,vdupq_n_f32(.5f)));q=vbslq_s32(vcltq_f32(x,vdupq_n_f32(0)),vnegq_s32(q),q);q=vaddq_s32(q,vdupq_n_s32(zp));int16x4_t h=vqmovn_s32(q);int8x8_t b=vqmovn_s16(vcombine_s16(h,h));uint32_t four=vget_lane_u32(vreinterpret_u32_s8(b),0);std::memcpy(out+i,&four,4);}
 }
 for(int i=blocks*4;i<count;i++){float v=in[i]/scale;out[i]=v<=-128-zp?-128:v>=127-zp?127:int8_t(round_even(v)+zp);}
#else
 quantize(in,out,count,scale,zp);
#endif
}
struct Ref {const int8_t* p=nullptr;int c=0,C=0,H=0,W=0;bool packed=false;const uint8_t* lut=nullptr;};
static size_t poff(int c,int y,int x,int C,int H,int W){
 int cb=c/32,co=std::min(32,C-cb*32),ty=y/16,tx=x/16,th=std::min(16,H-ty*16),tw=std::min(16,W-tx*16),g=c%32/8,lanes=std::min(8,co-g*8);
 return size_t(cb)*32*H*W+size_t(ty)*16*W*co+size_t(tx)*16*th*co+g*8*th*tw+((y%16)*tw+x%16)*lanes+c%8;
}
static int8_t get(const Ref&r,int y,int x){uint8_t v=r.p[r.packed?poff(r.c,y,x,r.C,r.H,r.W):size_t(r.c)*r.H*r.W+y*r.W+x];return int8_t(r.lut?r.lut[v]:v);}
struct Tensor {
 int type=0,rank=0;std::vector<int> d;size_t n=0;bool constant=false;
 std::vector<uint8_t> memory;uint8_t* p=nullptr;bool packed=false;
 std::vector<Ref> refs;
 void init(){n=1;for(int v:d)n*=v;memory.resize(n*bytes(type));p=memory.data();}
 void own(){p=memory.data();packed=false;refs.clear();}
 void root(bool pack=false){refs.clear();packed=pack;if(type==3&&rank==4){int C=d[1];for(int c=0;c<C;c++)refs.push_back({reinterpret_cast<int8_t*>(p),c,C,d[2],d[3],pack,nullptr});}}
 double value(size_t i)const{
  if(type==3&&!refs.empty()){int hw=d[2]*d[3],c=i/hw,s=i%hw;return get(refs[c],s/d[3],s%d[3]);}
  switch(type){case 1:return reinterpret_cast<const float*>(p)[i];case 2:case 9:return p[i];case 3:return reinterpret_cast<const int8_t*>(p)[i];case 6:return reinterpret_cast<const int32_t*>(p)[i];case 12:return reinterpret_cast<const uint32_t*>(p)[i];case 7:return double(reinterpret_cast<const int64_t*>(p)[i]);}return 0;
 }
 void put(size_t i,double x){switch(type){case 1:reinterpret_cast<float*>(p)[i]=float(x);break;case 2:case 9:p[i]=uint8_t(x);break;case 3:reinterpret_cast<int8_t*>(p)[i]=int8_t(x);break;case 6:reinterpret_cast<int32_t*>(p)[i]=int32_t(x);break;case 12:reinterpret_cast<uint32_t*>(p)[i]=uint32_t(x);break;case 7:reinterpret_cast<int64_t*>(p)[i]=int64_t(x);break;}}
};
struct Gather {size_t dst;int c,active,hi,wi,oy,ox,stride,pad,zp;};
struct Move {uint8_t*dst;const uint8_t*src;size_t length;const uint8_t*lut;int fill;};
struct DWPixel {uint8_t*dst;std::array<const uint8_t*,9> src;const uint8_t*lut;};
struct Node {int op;std::vector<int> in,out,a;std::vector<Gather> gathers,unique;std::vector<uint32_t> desc;size_t txoff=0,rxoff=0,txbytes=0,rxbytes=0,txsync=0,rxsync=0;void*txbo=nullptr,*rxbo=nullptr;uint8_t*txptr=nullptr,*rxptr=nullptr;uint64_t txaddr=0,rxaddr=0;std::vector<std::array<uint8_t,256>> maps;std::vector<Move> moves;std::vector<DWPixel> dw;std::vector<uint32_t> indices;double detail[16]={};bool planned=false,pair_skip=false,mirror=false;int pair_next=-1;size_t pair_bytes=0;std::vector<size_t>frame_offsets;};
struct Xrt {
 void* lib=nullptr,*device=nullptr,*tx=nullptr,*rx=nullptr;uint8_t*tp=nullptr,*rp=nullptr;uint64_t ta=0,ra=0;
 struct Buffer {void*bo;uint8_t*p;uint64_t address;size_t bytes;};std::vector<Buffer> parts;
 void*(*open)(unsigned)=nullptr;int(*close)(void*)=nullptr;void*(*alloc)(void*,size_t,uint64_t,unsigned)=nullptr;void*(*map)(void*)=nullptr;uint64_t(*address)(void*)=nullptr;int(*sync)(void*,int,size_t,size_t)=nullptr;int(*freebo)(void*)=nullptr;
 void init(size_t nt,size_t nr,bool pool_only=false){
#ifndef _WIN32
  lib=dlopen("libxrt_coreutil.so",RTLD_NOW|RTLD_LOCAL);check(lib,"dlopen XRT");
#define SYM(field,name) field=reinterpret_cast<decltype(field)>(dlsym(lib,name));check(field,"missing XRT C symbol " name)
  SYM(open,"xrtDeviceOpen");SYM(close,"xrtDeviceClose");SYM(alloc,"xrtBOAlloc");SYM(map,"xrtBOMap");SYM(address,"xrtBOAddress");SYM(sync,"xrtBOSync");SYM(freebo,"xrtBOFree");
#undef SYM
  device=open(0);check(device,"XRT device open");
  const char*mode=std::getenv("O7_CMA_MODE");
  // Default: persistent per-layer slot pool, each request < one layer packet.
  // Optional large arenas retain the earlier layout and fall back on failure.
  if(!pool_only&&mode&&std::strcmp(mode,"arena")==0){tx=alloc(device,nt,1ull<<24,0);rx=alloc(device,nr,1ull<<24,0);}
  // Fragmented CMA can reject a large arena even with no live leaked BOs.
  // Missing arenas fall back to small per-layer persistent BOs below.
  if(tx){tp=(uint8_t*)map(tx);ta=address(tx);check(tp&&ta<0x100000000ull,"XRT TX map/address");}
  if(rx){rp=(uint8_t*)map(rx);ra=address(rx);check(rp&&ra<0x100000000ull,"XRT RX map/address");}
#else
  throw std::runtime_error("hardware execution unavailable on Windows");
#endif
 }
 Buffer small(size_t nb){void*b=alloc(device,nb,1ull<<24,0);check(b,"XRT per-layer CMA allocation");Buffer v={b,(uint8_t*)map(b),address(b),nb};parts.push_back(v);check(v.p&&v.address<0x100000000ull,"XRT per-layer map/address");return v;}
 ~Xrt(){for(auto&v:parts)if(v.bo&&freebo)freebo(v.bo);if(rx&&freebo)freebo(rx);if(tx&&freebo)freebo(tx);if(device&&close)close(device);
#ifndef _WIN32
 if(lib)dlclose(lib);
#endif
 }
};
using Golden=int(*)(int,const int8_t*,int8_t*);
struct Engine {
 std::vector<Tensor> t;std::vector<Node> nodes;int input,output;volatile uint32_t*dma=nullptr,*core=nullptr;Golden golden=nullptr;
 Xrt xrt;std::vector<uint8_t> templates;size_t rxsize=0;std::vector<double> profile;double timers[16]={};int current=-1;std::vector<int8_t> tempin,tempout;bool initialized=false,neon_quant=false;int options=0;double detail[32]={};bool resident=false;uint32_t frame=0;std::vector<int>schedule;
 static int read(std::ifstream&f){int n;f.read((char*)&n,4);check(bool(f),"truncated program");return n;}
 Engine(const char*path,volatile uint32_t*d,volatile uint32_t*c,Golden g,const char*plan=nullptr,bool mirror_cache=false):dma(d),core(c),golden(g){
  std::ifstream f(path,std::ios::binary);check(bool(f),"program open");check(read(f)==0x3747504f,"program magic");int nt=read(f),nn=read(f);input=read(f);output=read(f);check(nt>0&&nt<20000&&nn<5000,"program size");t.resize(nt);
  for(auto&v:t){v.type=read(f);v.rank=read(f);check(v.rank>=0&&v.rank<=6,"tensor rank");for(int i=0;i<6;i++){int z=read(f);if(i<v.rank)v.d.push_back(z);}v.init();int nb=read(f);check(nb>=0&&nb<=int(v.memory.size()),"constant size");v.constant=nb!=0;if(nb)f.read((char*)v.p,nb);}
  for(int j=0;j<nn;j++){Node n;n.op=read(f);int ni=read(f),no=read(f),na=read(f);check(ni<30&&no<20&&na<40,"node shape");for(int i=0;i<ni;i++)n.in.push_back(read(f));for(int i=0;i<no;i++)n.out.push_back(read(f));for(int i=0;i<na;i++)n.a.push_back(read(f));nodes.push_back(std::move(n));}
  for(auto&v:t)if(v.type==3&&v.rank==4)v.root();profile.resize(nn);
  for(auto&n:nodes)if(n.op==1)prepare(n);
  for(size_t i=0;i<nodes.size();i++)schedule.push_back(i);
  resident_plan(plan,mirror_cache);
  if(dma){xrt.init(std::max(size_t(4096),templates.size()),std::max(size_t(4096),rxsize),resident);
   if(xrt.tx){std::memcpy(xrt.tp,templates.data(),templates.size());check(!xrt.sync(xrt.tx,0,templates.size(),0),"initial TX sync");}
   for(auto&n:nodes)if(n.op==1&&!n.pair_skip){
    if(xrt.tx){n.txbo=xrt.tx;n.txptr=xrt.tp+n.txoff;n.txaddr=xrt.ta+n.txoff;n.txsync=n.txoff;}
    else{auto b=xrt.small(n.txbytes);n.txbo=b.bo;n.txptr=b.p;n.txaddr=b.address;std::memcpy(n.txptr,templates.data()+n.txoff,n.txbytes);check(!xrt.sync(n.txbo,0,n.txbytes,0),"initial per-layer TX sync");}
    if(xrt.rx){n.rxbo=xrt.rx;n.rxptr=xrt.rp+n.rxoff;n.rxaddr=xrt.ra+n.rxoff;n.rxsync=n.rxoff;}
    else{auto b=xrt.small(n.rxbytes);n.rxbo=b.bo;n.rxptr=b.p;n.rxaddr=b.address;}
    auto&v=t[n.out[0]];if(n.pair_next<0||n.mirror){v.p=n.rxptr;v.root(true);}if(n.pair_next>=0){auto&w=t[nodes[n.pair_next].out[0]];w.p=n.rxptr+(n.mirror?n.pair_bytes:0);w.root(true);}
   }}
 }
 #include "resident_methods.inc"
 void prepare(Node&n){
  auto&a=n.a;int ci=a[1],co=a[2],k=a[3],stride=a[4],pad=a[5],mode=a[9];auto&in=t[n.in[0]];auto&out=t[n.out[0]];int h=in.d[2],w=in.d[3],oh=out.d[2],ow=out.d[3];
  n.txoff=(templates.size()+63)&~size_t(63);templates.resize(n.txoff);n.rxoff=(rxsize+63)&~size_t(63);n.rxbytes=out.n;rxsize=n.rxoff+n.rxbytes;
  int count=0,total=((co+31)/32)*((oh+15)/16)*((ow+15)/16),woff=0,ro=0;
  const uint8_t*weights=t[n.in[6]].p;
  auto append=[&](const void*p,size_t nb){size_t o=templates.size();templates.resize(o+nb);if(p)std::memcpy(templates.data()+o,p,nb);return o;};
  for(int oc=0;oc<co;oc+=32){int c=std::min(32,co-oc),wbtotal=0;for(int chunk=0;chunk<ci;chunk+=32)wbtotal+=((c+7)&~7)*((std::min(32,ci-chunk)+7)&~7)*k*k;
   for(int y=0;y<oh;y+=16)for(int x=0;x<ow;x+=16){int hh=std::min(16,oh-y),ww=std::min(16,ow-x),hi=(hh-1)*stride+k,wi=(ww-1)*stride+k,reuse=(x||y)?1:0;
    size_t hd=append(nullptr,76),start=templates.size();for(int j=2;j<=4;j++)append(t[n.in[j]].p+oc*4,c*4);if(mode==2)append(t[n.in[5]].p,256);
    int wo=woff;for(int chunk=0;chunk<ci;chunk+=32){int active=std::min(32,ci-chunk),cip=(active+7)&~7,wb=((c+7)&~7)*cip*k*k;if(!reuse)append(weights+wo,wb);wo+=wb;size_t dst=append(nullptr,cip*hi*wi);n.gathers.push_back({dst,chunk,active,hi,wi,y,x,stride,pad,a[6]});}
    uint32_t head[19]={0x51434f34,uint32_t(++count==total),uint32_t(ci),uint32_t(c),uint32_t(hi),uint32_t(wi),uint32_t(hh),uint32_t(ww),uint32_t(k),uint32_t(stride),uint32_t(a[6]&255),uint32_t(a[7]&255),uint32_t((templates.size()-start)/4),uint32_t(pad),uint32_t(a[8]&255),uint32_t(mode),1,uint32_t(reuse),uint32_t(((a[0]+1)<<8)|(oc/32))};std::memcpy(templates.data()+hd,head,76);
    uint32_t desc[7]={uint32_t(oc),uint32_t(y),uint32_t(x),uint32_t(c),uint32_t(hh),uint32_t(ww),uint32_t(ro/4)};n.desc.insert(n.desc.end(),desc,desc+7);ro+=c*hh*ww;
   }woff+=wbtotal;
  }n.txbytes=templates.size()-n.txoff;check(n.txbytes<8388608&&ro==int(n.rxbytes),"DMA packet bounds");
 }
 static void copy8(const Tensor&v,int c,int y,int x,int8_t*dst,int actual){
  if(c+8<=actual){const Ref&r=v.refs[c];bool same=r.c%8==0;for(int l=1;l<8&&same;l++)same=v.refs[c+l].p==r.p&&v.refs[c+l].c==r.c+l&&v.refs[c+l].lut==r.lut;
   if(same&&r.packed){const int8_t*p=r.p+poff(r.c,y,x,r.C,r.H,r.W);if(!r.lut)std::memcpy(dst,p,8);else for(int l=0;l<8;l++)dst[l]=r.lut[uint8_t(p[l])];return;}}
  for(int l=0;l<8;l++)dst[l]=c+l<actual?get(v.refs[c+l],y,x):0;
 }
 void gather(const Tensor&v,const Gather&g,uint8_t*dst){
  int H=v.d[2],W=v.d[3];bool nchw=!v.refs.empty()&&!v.refs[0].packed&&!v.refs[0].lut&&v.refs[0].c==0;for(int c=0;c<int(v.refs.size())&&nchw;c++)nchw=v.refs[c].p==v.refs[0].p&&v.refs[c].c==c;
  if(nchw){gather_activation(v.refs[0].p,v.d[1],H,W,g.c,g.active,g.hi,g.wi,g.oy,g.ox,g.stride,g.pad,g.zp,dst);return;}
  for(int gr=0;gr<((g.active+7)&~7);gr+=8)for(int yy=0;yy<g.hi;yy++){int sy=g.oy*g.stride-g.pad+yy;
   for(int xx=0;xx<g.wi;xx++){int sx=g.ox*g.stride-g.pad+xx;
    if(sy<0||sy>=H||sx<0||sx>=W){std::memset(dst,g.zp,8);}else {copy8(v,g.c+gr,sy,sx,(int8_t*)dst,g.c+g.active);for(int l=0;l<8;l++)if(gr+l>=g.active)dst[l]=g.zp;}dst+=8;
   }}
 }
 template<class F> void visit_i8(const Tensor&v,F fn){
  if(v.refs.empty()){for(size_t i=0;i<v.n;i++)fn(i,int8_t(v.p[i]));return;}
  int H=v.d[2],W=v.d[3];
  #pragma omp parallel for schedule(static) num_threads(2) if(v.n>=16384)
  for(int channel=0;channel<int(v.refs.size());channel++){const Ref&r=v.refs[channel];size_t out=size_t(channel)*H*W;int co=std::min(32,r.C-r.c/32*32),lanes=std::min(8,co-(r.c%32/8)*8);
   for(int y=0;y<H;y++)for(int x=0;x<W;){int span=r.packed?std::min(W-x,16-x%16):W-x;const uint8_t*p=(const uint8_t*)r.p+(r.packed?poff(r.c,y,x,r.C,r.H,r.W):size_t(r.c)*r.H*r.W+y*r.W+x);int step=r.packed?lanes:1;
    for(int j=0;j<span;j++){uint8_t q=p[j*step];fn(out++,int8_t(r.lut?r.lut[q]:q));}x+=span;
   }}
 }
 void material(const Tensor&v,int8_t*dst){visit_i8(v,[&](size_t i,int8_t q){dst[i]=q;});}
 // Signed INT8 zero points may be negative. A null source denotes fill;
 // testing fill>=0 would incorrectly treat negative padding as a copy.
 void moves(const std::vector<Move>&plan){for(const auto&m:plan){if(!m.src)std::memset(m.dst,m.fill,m.length);else if(!m.lut)std::memcpy(m.dst,m.src,m.length);else {size_t j=0;if(options&2)for(;j+8<=m.length;j+=8){for(int l=0;l<8;l++)m.dst[j+l]=m.lut[m.src[j+l]];}for(;j<m.length;j++)m.dst[j]=m.lut[m.src[j]];}}}
 void finish_plan(Node&n){
  if(options&1){std::vector<Move>merged;merged.reserve(n.moves.size());for(auto&m:n.moves){
   if(!merged.empty()){auto&z=merged.back();size_t length=z.length+m.length;bool same=z.dst+z.length==m.dst&&z.lut==m.lut&&bool(z.src)==bool(m.src);bool adjacent=!z.src?(z.fill==m.fill):(z.src+z.length==m.src);uintptr_t dp=(uintptr_t)z.dst,sp=(uintptr_t)z.src;bool overlap=z.src&&dp<sp+length&&sp<dp+length;
    if(same&&adjacent&&!overlap){z.length=length;continue;}}
   merged.push_back(m);}n.moves.swap(merged);}
  n.detail[8]=n.moves.size();for(auto&m:n.moves){int category=!m.src?2:m.lut?1:((uintptr_t)m.src>=(uintptr_t)n.txptr&&(uintptr_t)m.src<(uintptr_t)n.txptr+n.txbytes)?3:0;n.detail[9+category]+=m.length;}
 }

 void plan_moves(Node&n,const Tensor&v){
  std::map<std::array<int,7>,size_t> seen;
  for(const auto&g:n.gathers){std::array<int,7>key={g.c,g.active,g.hi,g.wi,g.oy,g.ox,g.stride};size_t length=((g.active+7)&~7)*g.hi*g.wi;auto found=seen.find(key);
   if(found!=seen.end()){n.moves.push_back({n.txptr+(g.dst-n.txoff),n.txptr+(found->second-n.txoff),length,nullptr,-1});continue;}seen[key]=g.dst;
   uint8_t*dst=n.txptr+(g.dst-n.txoff);int H=v.d[2],W=v.d[3];
   for(int gr=0;gr<((g.active+7)&~7);gr+=8)for(int yy=0;yy<g.hi;yy++){int sy=g.oy*g.stride-g.pad+yy;
    for(int xx=0;xx<g.wi;){int sx=g.ox*g.stride-g.pad+xx,span=1,c=g.c+gr;
     if(sy<0||sy>=H||sx<0||sx>=W){span=sy<0||sy>=H?g.wi-xx:sx<0?std::min(g.wi-xx,-sx):g.wi-xx;n.moves.push_back({dst,nullptr,size_t(span*8),nullptr,g.zp});}
     else {const Ref&r=v.refs[c];bool contiguous=gr+8<=g.active&&r.packed&&r.c%8==0;for(int l=1;l<8&&contiguous;l++)contiguous=v.refs[c+l].p==r.p&&v.refs[c+l].c==r.c+l&&v.refs[c+l].lut==r.lut;
      if(contiguous){span=std::min({g.wi-xx,W-sx,16-sx%16});n.moves.push_back({dst,(const uint8_t*)r.p+poff(r.c,sy,sx,r.C,r.H,r.W),size_t(span*8),r.lut,-1});}
      else {for(int l=0;l<8;l++){if(gr+l>=g.active)n.moves.push_back({dst+l,nullptr,1,nullptr,g.zp});else{auto&rr=v.refs[c+l];n.moves.push_back({dst+l,(const uint8_t*)rr.p+(rr.packed?poff(rr.c,sy,sx,rr.C,rr.H,rr.W):size_t(rr.c)*rr.H*rr.W+sy*rr.W+sx),1,rr.lut,-1});}}}
     }dst+=span*8;xx+=span;
    }}
  }finish_plan(n);n.planned=true;
 }
 static int8_t rq(int32_t v,uint32_t m,uint32_t s,int zp){int64_t z=int64_t(v)*m;bool neg=z<0;uint64_t a=neg?-z:z,q=a>>s,r=a&((uint64_t(1)<<s)-1),half=uint64_t(1)<<(s?s-1:0);q+=s&&(r>half||(r==half&&(q&1)));int64_t out=(neg?-int64_t(q):int64_t(q))+zp;return int8_t(std::max(int64_t(-128),std::min(int64_t(127),out)));}
 void convolution(Node&n){auto&v=t[n.in[0]];auto&out=t[n.out[0]];auto&a=n.a;
  if(golden&&(n.op==1||!std::getenv("O7_PC_NATIVE_DW"))){tempin.resize(v.n);tempout.resize(out.n);material(v,tempin.data());check(!golden(a[0],tempin.data(),tempout.data()),"PC integer Golden callback");out.own();bool packed=std::getenv("O7_PC_PACKED_GOLDEN");if(packed){int C=out.d[1],H=out.d[2],W=out.d[3];for(int c=0;c<C;c++)for(int y=0;y<H;y++)for(int x=0;x<W;x++)out.p[poff(c,y,x,C,H,W)]=tempout[(c*H+y)*W+x];}else std::memcpy(out.p,tempout.data(),out.n);out.root(packed);return;}
  if(n.op==2){double start=now();out.own();out.root(true);int C=a[1],H=v.d[2],W=v.d[3],K=a[3],OH=out.d[2],OW=out.d[3];auto*wt=(int8_t*)t[n.in[1]].p;auto*b=(int32_t*)t[n.in[2]].p;auto*m=(uint32_t*)t[n.in[3]].p;auto*s=(uint32_t*)t[n.in[4]].p;auto*lut=t[n.in[5]].p;
#ifdef __ARM_NEON
   bool planar=K==3&&a[4]==1&&a[5]==1;for(auto&r:v.refs)planar=planar&&!r.packed&&!r.lut&&r.H==H&&r.W==W;
   if(planar){
    #pragma omp parallel for schedule(static) num_threads(2) if(C*OH*OW>=4096)
    for(int c=0;c<C;c++){const Ref&r=v.refs[c];const int8_t*src=r.p+r.c*H*W;const int8_t*w=wt+c*9;
     for(int y=0;y<OH;y++){int x=0;while(x<OW){
      if(x>=1&&x+3<OW-1&&x%16+3<16){int32x4_t acc=vdupq_n_s32(b[c]);for(int ky=0;ky<3;ky++){int sy=y-1+ky;if(sy<0||sy>=H)continue;for(int kx=0;kx<3;kx++){uint32_t q;std::memcpy(&q,src+sy*W+x-1+kx,4);int8x8_t vv=vreinterpret_s8_u32(vdup_n_u32(q));int16x4_t xx=vsub_s16(vget_low_s16(vmovl_s8(vv)),vdup_n_s16(a[6]));acc=vmlal_n_s16(acc,xx,int(w[ky*3+kx])-a[7]);}}
       int32_t values[4];vst1q_s32(values,acc);int8_t*dst=(int8_t*)out.p+poff(c,y,x,C,OH,OW);for(int j=0;j<4;j++){int8_t q=rq(values[j],m[c],s[c],a[8]);dst[j*8]=a[9]==2?int8_t(lut[uint8_t(q)]):q;}x+=4;
      }else{int32_t acc=b[c];for(int ky=0;ky<3;ky++){int sy=y-1+ky;if(sy<0||sy>=H)continue;for(int kx=0;kx<3;kx++){int sx=x-1+kx;if(sx>=0&&sx<W)acc+=(int(src[sy*W+sx])-a[6])*(int(w[ky*3+kx])-a[7]);}}int8_t q=rq(acc,m[c],s[c],a[8]);out.p[poff(c,y,x,C,OH,OW)]=a[9]==2?lut[uint8_t(q)]:uint8_t(q);x++;}
     }}
    }timers[6]+=now()-start;return;
   }
#endif
   if(!n.planned){bool fast=K==3;for(int c=0;c<C;c+=8){auto&r=v.refs[c];fast=fast&&r.packed&&r.c%8==0;for(int l=1;l<8;l++)fast=fast&&v.refs[c+l].p==r.p&&v.refs[c+l].c==r.c+l&&v.refs[c+l].lut==r.lut;}
    if(fast)for(int c=0;c<C;c+=8)for(int y=0;y<OH;y++)for(int x=0;x<OW;x++){auto&r=v.refs[c];DWPixel p;p.dst=out.p+poff(c,y,x,C,OH,OW);p.lut=r.lut;
     for(int ky=0;ky<K;ky++)for(int kx=0;kx<K;kx++){int sy=y*a[4]-a[5]+ky,sx=x*a[4]-a[5]+kx;p.src[ky*K+kx]=sy<0||sy>=H||sx<0||sx>=W?nullptr:(const uint8_t*)r.p+poff(r.c,sy,sx,r.C,r.H,r.W);}n.dw.push_back(p);
    }n.planned=true;
   }
   #pragma omp parallel for schedule(static) num_threads(2) if(C*OH*OW>=8192)
   for(int cg=0;cg<C;cg+=8){
    int16_t kw[9][8];for(int z=0;z<K*K;z++)for(int l=0;l<8;l++)kw[z][l]=wt[(cg+l)*K*K+z]-a[7];
    for(int y=0;y<OH;y++)for(int x=0;x<OW;x++){int32_t acc[8];std::memcpy(acc,b+cg,32);
#ifdef __ARM_NEON
     int32x4_t lo=vld1q_s32(acc),hi=vld1q_s32(acc+4);
#endif
     for(int ky=0;ky<K;ky++)for(int kx=0;kx<K;kx++){int8_t val[8];const int8_t*vp=val;
      if(!n.dw.empty()){auto&p=n.dw[(cg/8*OH+y)*OW+x];auto*src=p.src[ky*K+kx];if(!src)continue;if(p.lut){for(int l=0;l<8;l++)val[l]=p.lut[src[l]];}else vp=(const int8_t*)src;}
      else{int sy=y*a[4]-a[5]+ky,sx=x*a[4]-a[5]+kx;if(sy<0||sy>=H||sx<0||sx>=W)continue;copy8(v,cg,sy,sx,val,C);}
#ifdef __ARM_NEON
      int16x8_t xx=vsubq_s16(vmovl_s8(vld1_s8(vp)),vdupq_n_s16(a[6])),ww=vld1q_s16(kw[ky*K+kx]);lo=vmlal_s16(lo,vget_low_s16(xx),vget_low_s16(ww));hi=vmlal_s16(hi,vget_high_s16(xx),vget_high_s16(ww));
#else
      for(int l=0;l<8;l++)acc[l]+=(int(vp[l])-a[6])*kw[ky*K+kx][l];
#endif
     }
#ifdef __ARM_NEON
     vst1q_s32(acc,lo);vst1q_s32(acc+4,hi);
#endif
     int8_t*dst=!n.dw.empty()?(int8_t*)n.dw[(cg/8*OH+y)*OW+x].dst:(int8_t*)out.p+poff(cg,y,x,C,OH,OW);for(int l=0;l<8;l++){int8_t q=rq(acc[l],m[cg+l],s[cg+l],a[8]);dst[l]=a[9]==2?int8_t(lut[uint8_t(q)]):q;}
    }}timers[6]+=now()-start;return;
  }
  check(dma&&core,"missing hardware device");for(size_t off:n.frame_offsets){uint32_t*stamp=(uint32_t*)(n.txptr+off);*stamp=frame;}double start=now();
  bool simple=!v.refs[0].packed&&!v.refs[0].lut&&v.refs[0].c==0;for(int c=0;c<int(v.refs.size())&&simple;c++)simple=v.refs[c].p==v.refs[0].p&&v.refs[c].c==c&&!v.refs[c].lut;
  if(simple){if(!n.planned){std::map<std::array<int,7>,size_t>seen;for(const auto&g:n.gathers){std::array<int,7>key={g.c,g.active,g.hi,g.wi,g.oy,g.ox,g.stride};auto it=seen.find(key);if(it==seen.end()){seen[key]=g.dst;n.unique.push_back(g);}else n.moves.push_back({n.txptr+(g.dst-n.txoff),n.txptr+(it->second-n.txoff),size_t(((g.active+7)&~7)*g.hi*g.wi),nullptr,-1});}finish_plan(n);n.planned=true;}
   for(const auto&g:n.unique)gather_activation(v.refs[0].p,v.d[1],v.d[2],v.d[3],g.c,g.active,g.hi,g.wi,g.oy,g.ox,g.stride,g.pad,g.zp,n.txptr+(g.dst-n.txoff));moves(n.moves);
  }else{if(!n.planned)plan_moves(n,v);moves(n.moves);}
  timers[0]+=now()-start;
  start=now();check(!xrt.sync(n.txbo,0,n.txbytes,n.txsync),"TX cache sync");double synced=now();int rc=submit_dma(dma,core,n.txaddr,n.rxaddr,n.txbytes,n.rxbytes,0);check(!rc,"DMA submit");double submitted=now();uint32_t counts[11],state[3];rc=wait_queue(dma,core,counts,state);double polled=now();check(!rc,"DMA wait/status/timeout");check(counts[6]==n.txbytes/4&&counts[7]==n.rxbytes/4&&counts[8]==n.desc.size()/7,"DMA packet counter mismatch");check(!xrt.sync(n.rxbo,1,n.rxbytes,n.rxsync),"RX cache sync");double received=now();n.detail[0]=synced-start;n.detail[1]=submitted-synced;n.detail[2]=polled-submitted;n.detail[3]=received-polled;for(int z=0;z<4;z++)detail[z]+=n.detail[z];timers[1]+=received-start;timers[3]+=counts[0]*.00001;timers[4]+=counts[3]*.00001;timers[8]+=n.txbytes;timers[9]+=n.rxbytes;timers[11]+=core[0x180/4];timers[12]+=core[0x184/4];
  if(n.pair_next<0||n.mirror){out.p=n.rxptr;out.root(true);}
  if(n.pair_next>=0){auto&last=t[nodes[n.pair_next].out[0]];last.p=n.rxptr+(n.mirror?n.pair_bytes:0);last.root(true);check(core[0x200/4]==n.pair_bytes,"actual resident write byte count");for(int z=0;z<16;z++)detail[16+z]+=core[0x200/4+z];}
 }
 static size_t broadcast(const Tensor&v,const Tensor&o,size_t i){size_t idx=0,stride=1;for(int j=int(o.d.size())-1,k=int(v.d.size())-1;j>=0;j--,k--){int c=i%o.d[j];i/=o.d[j];if(k>=0){idx+=(v.d[k]==1?0:c)*stride;stride*=v.d[k];}}return idx;}
 void runnode(Node&n){auto&v=t[n.in[0]];auto&o=t[n.out[0]];auto&a=n.a;int op=n.op;if(op==1||op==2){convolution(n);return;}
  if(op==3||op==15||op==24||op==27){if(!v.refs.empty()&&o.d!=v.d){o.own();material(v,(int8_t*)o.p);o.root();}else{o.p=v.p;o.refs=v.refs;o.packed=v.packed;}return;}
  if(op==4){o.p=v.p;o.refs=v.refs;o.packed=v.packed;auto*lut=t[n.in[1]].p;if(!o.refs.empty()){n.maps.resize(o.refs.size());for(size_t c=0;c<o.refs.size();c++){auto&r=o.refs[c];if(r.lut){if(!initialized)for(int j=0;j<256;j++)n.maps[c][j]=lut[r.lut[j]];r.lut=n.maps[c].data();}else r.lut=lut;}return;}}
  // Channel-only split/concat INT8 tensors retain a virtual packed channel map.
  if(op==14&&v.type==3&&v.rank==4&&a[0]==1){int c=0;for(int id:n.out){auto&z=t[id];z.p=v.p;z.refs.assign(v.refs.begin()+c,v.refs.begin()+c+z.d[1]);z.packed=true;c+=z.d[1];}return;}
  if(op==13&&o.type==3&&o.rank==4&&a[0]==1){o.refs.clear();for(int id:n.in)o.refs.insert(o.refs.end(),t[id].refs.begin(),t[id].refs.end());o.p=v.p;o.packed=true;return;}
  o.own();
  if(op==5||op==7){float*out=(float*)o.p;float table[256];const float*lut;
   if(op==5)lut=(const float*)t[n.in[1]].p;else{float scale=t[n.in[1]].value(0);int zp=t[n.in[2]].value(0);for(int j=0;j<256;j++)table[j]=(int(int8_t(j))-zp)*scale;lut=table;}
   visit_i8(v,[&](size_t i,int8_t q){out[i]=lut[uint8_t(q)];});return;
  }
  if(op==6&&v.type==1&&o.type==3){auto fn=neon_quant?fast_quantize:quantize;fn((const float*)v.p,(int8_t*)o.p,int(o.n),float(t[n.in[1]].value(0)),int(t[n.in[2]].value(0)));o.root();return;}
  if(op==4||op==5||op==6||op==7||op==8||op==30){auto*tab=n.in.size()>1?t[n.in[1]].p:nullptr;float scale=n.in.size()>1?float(t[n.in[1]].value(0)):1;int zp=n.in.size()>2?int(t[n.in[2]].value(0)):0;
   for(size_t i=0;i<o.n;i++){float x=float(v.value(i));double y=0;if(op==4)y=((int8_t*)tab)[uint8_t(int8_t(x))];else if(op==5)y=((float*)tab)[uint8_t(int8_t(x))];else if(op==6){float z=x/scale;y=std::max(-128,std::min(127,round_even(z)+zp));}else if(op==7)y=(int(x)-zp)*scale;else if(op==8)y=x/(1.f+std::exp(-x));else y=1.f/(1.f+std::exp(-x));o.put(i,y);}o.root();return;
  }
  if(op>=9&&op<=12&&v.type==1&&t[n.in[1]].type==1&&o.type==1){auto&b=t[n.in[1]];
   if(v.n==o.n&&(b.n==o.n||b.n==1)){const float*xx=(const float*)v.p,*yy=(const float*)b.p;float*out=(float*)o.p;int count=int(o.n);float scalar=yy[0];int j=0;
#ifdef __ARM_NEON
    for(;j+4<=count;j+=4){float32x4_t x=vld1q_f32(xx+j),y=b.n==1?vdupq_n_f32(scalar):vld1q_f32(yy+j);if(op==9)vst1q_f32(out+j,vaddq_f32(x,y));else if(op==10)vst1q_f32(out+j,vsubq_f32(x,y));else if(op==11)vst1q_f32(out+j,vmulq_f32(x,y));else break;}
#endif
    for(;j<count;j++){float x=xx[j],y=b.n==1?scalar:yy[j];out[j]=op==9?x+y:op==10?x-y:op==11?x*y:x/y;}return;
   }}
  if(op>=9&&op<=12||op==29){auto&b=t[n.in[1]];for(size_t i=0;i<o.n;i++){double av=v.value(broadcast(v,o,i)),bv=b.value(broadcast(b,o,i)),r=0;
    if(o.type==1){float x=av,y=bv;r=op==9?x+y:op==10?x-y:op==11?x*y:x/y;}else r=op==9?av+bv:op==10?av-bv:op==11?av*bv:op==29?std::fmod(av,bv):std::floor(av/bv);o.put(i,r);}o.root();return;}
  if(op==13){int axis=a[0];if(axis<0)axis+=o.rank;size_t outer=1,inner=1;for(int j=0;j<axis;j++)outer*=o.d[j];for(int j=axis+1;j<o.rank;j++)inner*=o.d[j];for(size_t b=0;b<outer;b++){size_t offset=b*o.d[axis]*inner;for(int id:n.in){auto&z=t[id];size_t size=z.d[axis]*inner;if(z.refs.empty())std::memcpy(o.p+offset*bytes(o.type),z.p+b*size*bytes(z.type),size*bytes(z.type));else for(size_t j=0;j<size;j++)o.put(offset+j,z.value(b*size+j));offset+=size;}}o.root();return;}
  if(op==14){int axis=a[0];if(axis<0)axis+=v.rank;size_t outer=1,inner=1;for(int j=0;j<axis;j++)outer*=v.d[j];for(int j=axis+1;j<v.rank;j++)inner*=v.d[j];bool linear=v.refs.empty();if(!linear){linear=true;for(int c=0;c<int(v.refs.size());c++){auto&r=v.refs[c];linear=linear&&!r.packed&&!r.lut&&r.p==(int8_t*)v.p&&r.c==c&&r.H==v.d[2]&&r.W==v.d[3];}}
   size_t start=0;for(int id:n.out){auto&z=t[id];z.own();size_t size=z.d[axis]*inner;for(size_t b=0;b<outer;b++){if(linear)std::memcpy(z.p+b*size*bytes(z.type),v.p+(b*v.d[axis]*inner+start)*bytes(v.type),size*bytes(z.type));else for(size_t j=0;j<size;j++)z.put(b*size+j,v.value(b*v.d[axis]*inner+start+j));}start+=size;z.root();}return;}
  if(op==16){if(n.indices.empty()){n.indices.resize(o.n);std::vector<size_t> strides(v.rank,1);for(int j=v.rank-2;j>=0;j--)strides[j]=strides[j+1]*v.d[j+1];for(size_t i=0;i<o.n;i++){size_t z=i,src=0;for(int j=o.rank-1;j>=0;j--){src+=(z%o.d[j])*strides[a[j]];z/=o.d[j];}n.indices[i]=src;}}if(v.type==1){float*out=(float*)o.p;const float*in=(float*)v.p;for(size_t i=0;i<o.n;i++)out[i]=in[n.indices[i]];}else for(size_t i=0;i<o.n;i++)o.put(i,v.value(n.indices[i]));return;}
  if(op==17){auto&b=t[n.in[1]];int m=v.d[v.rank-2],k=v.d.back(),nn=b.d.back();size_t batches=o.n/(m*nn);check(v.type==1&&b.type==1,"MatMul dtype");for(size_t z=0;z<batches;z++)matmul((float*)v.p+z*m*k,(float*)b.p+z*k*nn,(float*)o.p+z*m*nn,m,nn,k);return;}
  if(op==18){int axis=a[0];if(axis<0)axis+=v.rank;check(axis==v.rank-1,"Softmax axis");int cols=v.d.back();for(size_t row=0;row<o.n/cols;row++){float mx=-INFINITY;for(int j=0;j<cols;j++)mx=std::max(mx,float(v.value(row*cols+j)));float sum=0;for(int j=0;j<cols;j++){float e=std::exp(float(v.value(row*cols+j))-mx);((float*)o.p)[row*cols+j]=e;sum+=e;}for(int j=0;j<cols;j++)((float*)o.p)[row*cols+j]/=sum;}return;}
  if(op==19){check(v.type==1&&v.d==o.d,"MaxPool shape");std::vector<float>scratch(o.n);maxpool_float((float*)v.p,(float*)o.p,scratch.data(),v.d[1],v.d[2],v.d[3],a[0]);return;}
  if(op==20){int H=v.d[2],W=v.d[3],OH=o.d[2],OW=o.d[3];if(v.type==3){o.root(true);if(!n.planned){for(int c=0;c<v.d[1];c+=8)for(int y=0;y<OH;y++)for(int x=0;x<OW;x++){auto&r=v.refs[c];int sy=y*H/OH,sx=x*W/OW;uint8_t*dst=o.p+poff(c,y,x,o.d[1],OH,OW);bool same=r.packed&&r.c%8==0;for(int l=1;l<8&&same;l++)same=v.refs[c+l].p==r.p&&v.refs[c+l].c==r.c+l&&v.refs[c+l].lut==r.lut;
    if(same)n.moves.push_back({dst,(const uint8_t*)r.p+poff(r.c,sy,sx,r.C,r.H,r.W),8,r.lut,-1});else for(int l=0;l<8;l++){auto&rr=v.refs[c+l];n.moves.push_back({dst+l,(const uint8_t*)rr.p+(rr.packed?poff(rr.c,sy,sx,rr.C,rr.H,rr.W):size_t(rr.c)*rr.H*rr.W+sy*rr.W+sx),1,rr.lut,-1});}}n.planned=true;}moves(n.moves);return;}
   for(int c=0;c<v.d[1];c++)for(int y=0;y<OH;y++)for(int x=0;x<OW;x++)o.put((c*OH+y)*OW+x,v.value((c*H+y*H/OH)*W+x*W/OW));o.root();return;}
  if(op==21){std::vector<int>starts(v.rank,0),steps(v.rank,1);auto&st=t[n.in[1]];auto&en=t[n.in[2]];for(size_t j=0;j<st.n;j++){int ax=n.in.size()>3&&n.in[3]>=0?int(t[n.in[3]].value(j)):j;int step=n.in.size()>4&&n.in[4]>=0?int(t[n.in[4]].value(j)):1;int s=int(st.value(j));if(s<0)s+=v.d[ax];starts[ax]=std::max(0,std::min(v.d[ax],s));steps[ax]=step;}for(size_t i=0;i<o.n;i++){size_t rem=i,src=0,stride=1;for(int j=o.rank-1;j>=0;j--){int c=rem%o.d[j];rem/=o.d[j];src+=(starts[j]+c*steps[j])*stride;stride*=v.d[j];}o.put(i,v.value(src));}o.root();return;}
  if(op==22){check(a.size()==2&&(a[1]==-1||a[1]==v.rank-1),"ReduceMax axes");int cols=v.d.back();check(v.type==1&&o.type==1,"ReduceMax type");const float*in=(const float*)v.p;float*out=(float*)o.p;for(size_t i=0;i<o.n;i++){float mx=-INFINITY;for(int j=0;j<cols;j++)mx=std::max(mx,in[i*cols+j]);out[i]=mx;}return;}
  if(op==23){int axis=a[0];if(axis<0)axis+=v.rank;check(axis==v.rank-1,"TopK axis");int cols=v.d.back(),k=o.d.back();auto&indices=t[n.out[1]];indices.own();std::vector<int>order(cols);for(size_t row=0;row<v.n/cols;row++){std::iota(order.begin(),order.end(),0);auto cmp=[&](int i,int j){float x=v.value(row*cols+i),y=v.value(row*cols+j);return x==y?i<j:(a[1]?x>y:x<y);};if(k<cols)std::nth_element(order.begin(),order.begin()+k,order.end(),cmp);std::sort(order.begin(),order.begin()+k,cmp);for(int j=0;j<k;j++){o.put(row*k+j,v.value(row*cols+order[j]));indices.put(row*k+j,order[j]);}}return;}
  if(op==25){if(n.indices.empty()){n.indices.resize(o.n);for(size_t i=0;i<o.n;i++)n.indices[i]=broadcast(v,o,i);}if(v.type==7){auto*in=(const int64_t*)v.p;auto*out=(int64_t*)o.p;for(size_t i=0;i<o.n;i++)out[i]=in[n.indices[i]];}else for(size_t i=0;i<o.n;i++)o.put(i,v.value(n.indices[i]));return;}
  if(op==26){int axis=a[0];if(axis<0)axis+=v.rank;auto&ix=t[n.in[1]];int inner=1,outer=1;for(int j=axis+1;j<v.rank;j++)inner*=v.d[j];for(int j=0;j<axis;j++)outer*=v.d[j];check(ix.type==7,"GatherElements index type");auto*indices=(const int64_t*)ix.p;
   for(int b=0;b<outer;b++)for(int j=0;j<o.d[axis];j++)for(int k=0;k<inner;k++){size_t i=(b*o.d[axis]+j)*inner+k;I index=indices[i];if(index<0)index+=v.d[axis];check(index>=0&&index<v.d[axis],"GatherElements index");size_t src=(b*v.d[axis]+int(index))*inner+k;if(v.type==1)((float*)o.p)[i]=((const float*)v.p)[src];else if(v.type==7)((int64_t*)o.p)[i]=((const int64_t*)v.p)[src];else o.put(i,v.value(src));}return;}
  if(op==28){for(size_t i=0;i<o.n;i++)o.put(i,v.value(i));return;}
  throw std::runtime_error("unsupported opcode "+std::to_string(op));
 }
 void run(const float*x,float*out,const uint8_t*bgr=nullptr){std::fill(timers,timers+16,0.);std::fill(detail,detail+32,0.);std::fill(profile.begin(),profile.end(),0.);frame++;double start=now();auto&v=t[input];int first=0;
  if(bgr){check(nodes[0].op==6&&nodes[0].in[0]==input&&v.rank==4&&v.d[1]==3,"BGR input contract");auto&n=nodes[0];auto&q=t[n.out[0]];q.own();q.root();float scale=t[n.in[1]].value(0);int zp=t[n.in[2]].value(0);int8_t tab[256];for(int j=0;j<256;j++){float norm=float(j)/255.f;float z=norm/scale;tab[j]=int8_t(std::max(-128,std::min(127,round_even(z)+zp)));}
   int pixels=v.d[2]*v.d[3];int8_t*dst=(int8_t*)q.p;for(int j=0;j<pixels;j++){dst[j]=tab[bgr[j*3+2]];dst[pixels+j]=tab[bgr[j*3+1]];dst[2*pixels+j]=tab[bgr[j*3]];}first=1;timers[10]=now()-start;profile[0]=timers[10];
  }else{v.own();std::memcpy(v.p,x,v.n*4);}
  for(size_t step=0;step<schedule.size();step++){size_t i=schedule[step];if(i<size_t(first)||nodes[i].pair_skip)continue;current=i;double s=now();runnode(nodes[i]);profile[i]=now()-s;}auto&o=t[output];for(size_t i=0;i<o.n;i++)out[i]=float(o.value(i));timers[7]=now()-start;timers[5]=timers[7]-timers[0]-timers[1]-timers[2];initialized=true;}
};
}
extern "C" {
void o7_quantize_exact(const float*x,int8_t*out,int count,float scale,int zp){o7::fast_quantize(x,out,count,scale,zp);}
void o7_set_quantization_mode(void*p,int mode){((o7::Engine*)p)->neon_quant=mode!=0;}
void o7_memory(void*p,uint64_t*out){auto*g=(o7::Engine*)p;uint64_t tensors=0,plans=0;for(auto&t:g->t)tensors+=t.memory.capacity();for(auto&n:g->nodes)plans+=n.moves.capacity()*sizeof(o7::Move)+n.dw.capacity()*sizeof(o7::DWPixel)+n.indices.capacity()*4;out[0]=g->templates.size();out[1]=g->rxsize;out[2]=tensors;out[3]=plans;}
void o7_memory_extended(void*p,uint64_t*out){o7_memory(p,out);auto*g=(o7::Engine*)p;uint64_t count=0,tx=0,rx=0;for(auto&n:g->nodes)if(n.op==1){count++;tx+=n.txbytes;rx+=n.rxbytes;}if(!g->xrt.tx)out[0]=tx;if(!g->xrt.rx)out[1]=rx;out[4]=g->xrt.tx?1:count;out[5]=g->xrt.rx?1:count;out[6]=!g->xrt.tx;out[7]=!g->xrt.rx;}
void* o7_create(const char*path,void*dma,void*core,o7::Golden golden){try{return new o7::Engine(path,(volatile uint32_t*)dma,(volatile uint32_t*)core,golden);}catch(const std::exception&e){o7::error=e.what();return nullptr;}}
int o7_run(void*p,const float*x,float*out){auto*g=(o7::Engine*)p;try{g->run(x,out);return 0;}catch(const std::exception&e){o7::error="node "+std::to_string(g->current)+": "+e.what();return -1;}}
int o7_run_bgr(void*p,const uint8_t*x,float*out){auto*g=(o7::Engine*)p;try{g->run(nullptr,out,x);return 0;}catch(const std::exception&e){o7::error="node "+std::to_string(g->current)+": "+e.what();return -1;}}
void o7_destroy(void*p){delete(o7::Engine*)p;}
const char*o7_error(){return o7::error.c_str();}
void o7_timers(void*p,double*out){std::memcpy(out,((o7::Engine*)p)->timers,16*8);}
void o7_profile(void*p,double*out){auto*g=(o7::Engine*)p;std::memcpy(out,g->profile.data(),g->profile.size()*8);}
int o7_tensor(void*p,int id,void*out,size_t capacity){auto*g=(o7::Engine*)p;try{auto&v=g->t.at(id);o7::check(capacity>=v.n*o7::bytes(v.type),"tensor copy capacity");if(v.type==3&&!v.refs.empty())g->material(v,(int8_t*)out);else std::memcpy(out,v.p,v.n*o7::bytes(v.type));return 0;}catch(const std::exception&e){o7::error=e.what();return -1;}}
}

extern "C" {
int o8_set_options(void*p,int options){auto*g=(o7::Engine*)p;if(g->initialized)return -1;g->options=options;return 0;}
void o8_detail(void*p,double*out){std::memcpy(out,((o7::Engine*)p)->detail,32*8);}
void o8_node_detail(void*p,double*out){auto*g=(o7::Engine*)p;for(size_t i=0;i<g->nodes.size();i++)std::memcpy(out+i*16,g->nodes[i].detail,16*8);}
}

extern "C" void*o8_create(const char*path,void*dma,void*core,o7::Golden golden,const char*plan,int debug_mirror){try{return new o7::Engine(path,(volatile uint32_t*)dma,(volatile uint32_t*)core,golden,plan,debug_mirror!=0);}catch(const std::exception&e){o7::error=e.what();return nullptr;}}
