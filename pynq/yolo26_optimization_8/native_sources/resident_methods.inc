// Included inside Engine. Arithmetic nodes and original graph.bin are unchanged.
 void resident_plan(const char*file,bool mirror){
  if(!file||!file[0])return;
  std::ifstream f(file,std::ios::binary);check(bool(f),"resident plan open");
  check(read(f)==0x3852504f&&read(f)==1,"resident plan version");
  check(read(f)==131072&&read(f)==0x80001,"resident capability/capacity");
  check(read(f)==int(nodes.size()),"resident graph node count");int np=read(f),ns=read(f);read(f);
  check(np>0&&np<48&&ns==int(nodes.size()),"resident plan count");char hash[32];f.read(hash,32);check(bool(f),"resident SHA link");
  struct Pair {int a,b,id,bytes,C,H,W,token;};std::vector<Pair> pairs;std::vector<int> used(nodes.size(),0);
  for(int z=0;z<np;z++){
   int v[8];for(int j=0;j<8;j++)v[j]=read(f);Pair p{v[0],v[1],v[2],v[3],v[4],v[5],v[6],v[7]};
   check(p.a>=0&&p.b>=0&&p.a<int(nodes.size())&&p.b<int(nodes.size())&&p.a!=p.b,"resident node index");
   check(!used[p.a]&&!used[p.b],"overlapping resident pair");used[p.a]=used[p.b]=1;
   auto&a=nodes[p.a];auto&b=nodes[p.b];check(a.op==1&&b.op==1&&a.out[0]==p.id&&b.in[0]==p.id,"resident direct dense edge");
   int consumers=0;for(auto&n:nodes)for(int id:n.in)consumers+=id==p.id;
   check(consumers==1,"resident fan-out prohibited");auto&vout=t[p.id];
   check(vout.rank==4&&vout.d[0]==1&&vout.d[1]==p.C&&vout.d[2]==p.H&&vout.d[3]==p.W&&vout.n==size_t(p.bytes),"resident tensor dimensions");
   check(p.C>0&&p.C<=512&&p.C%8==0&&p.H>0&&p.H<=256&&p.W>0&&p.W<=256&&p.bytes>0&&p.bytes<=131072,"resident capacity boundary");
   for(auto*n:{&a,&b}){int ci=n->a[1],co=std::min(32,n->a[2]),k=n->a[3];check(ci<=512&&((co+15)/16)*((ci+7)/8)*k*k<=512,"resident weight bank bounds");}
   pairs.push_back(p);
  }
  schedule.clear();std::vector<int>positions(nodes.size(),-1);
  for(int j=0;j<ns;j++){int id=read(f);check(id>=0&&id<ns&&positions[id]<0,"resident schedule permutation");positions[id]=j;schedule.push_back(id);}
  std::vector<int> writer(t.size(),-1);for(int i=0;i<ns;i++)for(int id:nodes[i].out){check(writer[id]<0,"multiple tensor writer");writer[id]=i;}
  for(int i=0;i<ns;i++)for(int id:nodes[i].in)if(id>=0&&writer[id]>=0)check(positions[writer[id]]<positions[i],"resident schedule dependency");
  if(!dma)return; // PC executes every original arithmetic node in the proved order.
  check(core&&core[1]==0x80001&&core[2]==0x8000f&&core[3]==131072,"required O8 resident firmware is not loaded");
  resident=true;
  const std::vector<uint8_t>old=templates;
  for(auto&p:pairs){
   Node&a=nodes[p.a];Node&b=nodes[p.b];size_t abase=a.txoff,bbase=b.txoff,an=a.txbytes,bn=b.txbytes;
   const auto ag=a.gathers;const auto bg=b.gathers;std::vector<Gather>dynamic;std::vector<uint8_t>packet;
   size_t base=(templates.size()+63)&~size_t(63);templates.resize(base);
   auto append=[&](const void*src,size_t nb){size_t off=packet.size();packet.resize(off+nb);if(src)std::memcpy(packet.data()+off,src,nb);return off;};
   a.frame_offsets.clear();
   for(int layer=0;layer<2;layer++){
    Node&n=layer?b:a;size_t begin=layer?bbase:abase,extent=layer?bn:an,pos=begin;size_t gi=0,tile=0,nt=n.desc.size()/7;const auto&gathers=layer?bg:ag;
    while(pos<begin+extent){
     const uint32_t*h=(const uint32_t*)(old.data()+pos);check(h[0]==0x51434f34,"resident source packet");
     int ci=h[2],co=h[3],k=h[8],mode=h[15],reuse=h[17];size_t hd=append(nullptr,112),pay=packet.size(),src=pos+76;
     size_t params=co*12+(mode==2?256:0);append(old.data()+src,params);src+=params;
     for(int ic=0;ic<ci;ic+=32){int cp=(std::min(32,ci-ic)+7)&~7,wb=((co+7)&~7)*cp*k*k,ab=cp*h[4]*h[5];
      if(!reuse){append(old.data()+src,wb);src+=wb;}
      check(gi<gathers.size()&&gathers[gi].dst==src,"resident activation source bounds");
      if(!layer){Gather g=gathers[gi];g.dst=base+packet.size();dynamic.push_back(g);append(old.data()+src,ab);}src+=ab;gi++;
     }
     check(src==pos+76+h[12]*4,"resident source payload consumed");
     uint32_t header[28]={};std::memcpy(header,h,76);header[0]=0x51434f38;
     header[1]=layer?(2u|(tile+1==nt?1u:0u)):(4u|(tile==0?8u:0u)|(tile+1==nt?16u:0u)|(mirror?64u:0u));
     header[19]=(packet.size()-pay)/4;header[20]=p.token;header[21]=p.C;header[22]=p.H;header[23]=p.W;
     header[24]=n.desc[tile*7+1]*h[9];header[25]=n.desc[tile*7+2]*h[9];header[26]=p.bytes;header[27]=0;
     std::memcpy(packet.data()+hd,header,112);a.frame_offsets.push_back(hd+108);pos=src;tile++;
    }check(gi==gathers.size()&&tile==nt,"resident descriptor/gather count");
   }
   a.txoff=base;a.txbytes=packet.size();check(a.txbytes>0&&a.txbytes<8388608,"resident Simple DMA TX limit");templates.insert(templates.end(),packet.begin(),packet.end());
   a.gathers.swap(dynamic);a.rxbytes=t[b.out[0]].n+(mirror?size_t(p.bytes):0);check(a.rxbytes&&a.rxbytes<8388608,"resident Simple DMA RX limit");
   a.desc.insert(a.desc.end(),b.desc.begin(),b.desc.end());a.pair_next=p.b;a.pair_bytes=p.bytes;a.mirror=mirror;b.pair_skip=true;
  }
 }
