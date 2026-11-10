// Exact FloatLookup/DQ -> FP32 Add -> Q table composition. No INT8 Add substitute.
// Every float table entry, Add rounding and Q division is formed by the same
// scalar operations as the original graph (-ffp-contract=off, no fast-math).
 void prepare_software_fusion(){
  if(!(options&4))return;
  std::vector<int>writers(t.size(),-1),users(t.size(),0);
  for(size_t i=0;i<nodes.size();i++){for(int id:nodes[i].out)writers[id]=i;for(int id:nodes[i].in)if(id>=0)users[id]++;}
  for(auto&q:nodes){
   if(q.op!=6||q.in.empty())continue;int ai=writers[q.in[0]];if(ai<0)continue;auto&add=nodes[ai];
   if(add.op!=9||add.in.size()!=2||users[add.out[0]]!=1)continue;
   int li=writers[add.in[0]],ri=writers[add.in[1]];if(li<0||ri<0||li==ri)continue;
   auto&l=nodes[li];auto&r=nodes[ri];if(!((l.op==5||l.op==7)&&(r.op==5||r.op==7)))continue;
   if(users[l.out[0]]!=1||users[r.out[0]]!=1)continue;
   auto&x=t[l.in[0]];auto&y=t[r.in[0]];auto&o=t[q.out[0]];
   if(x.type!=3||y.type!=3||x.rank!=4||x.d!=y.d||x.d!=o.d||x.d[1]%8!=0)continue;
   std::array<float,256>lt,rt;
   for(int side=0;side<2;side++){auto&n=side?r:l;auto&tab=side?rt:lt;
    if(n.op==5)std::memcpy(tab.data(),t[n.in[1]].p,256*4);
    else{float scale=t[n.in[1]].value(0);int zp=t[n.in[2]].value(0);for(int j=0;j<256;j++)tab[j]=(int(int8_t(j))-zp)*scale;}
   }
   std::vector<float>sums(65536);for(int i=0;i<256;i++)for(int j=0;j<256;j++)sums[i*256+j]=lt[i]+rt[j];
   q.fused_table.resize(65536);quantize(sums.data(),(int8_t*)q.fused_table.data(),65536,float(t[q.in[1]].value(0)),int(t[q.in[2]].value(0)));
   q.fused_left=l.in[0];q.fused_right=r.in[0];l.software_skip=true;r.software_skip=true;add.software_skip=true;
  }
 }
 void fused_add_quant(Node&n){
  auto&x=t[n.fused_left];auto&y=t[n.fused_right];auto&o=t[n.out[0]];o.own();o.root(true);int C=o.d[1],H=o.d[2],W=o.d[3];
  if(!n.fused_ready){
   n.fused_fast=true;
   for(int c=0;c<C;c+=8)for(auto*v:{&x,&y}){
    auto&r=v->refs[c];bool same=r.packed&&r.c%8==0;
    for(int l=1;l<8&&same;l++)same=v->refs[c+l].p==r.p&&v->refs[c+l].c==r.c+l&&v->refs[c+l].lut==r.lut;
    n.fused_fast=n.fused_fast&&same;
   }
   if(n.fused_fast){
    n.fused_moves.reserve(o.n/8);
    for(int c=0;c<C;c+=8)for(int yy=0;yy<H;yy++)for(int xx=0;xx<W;xx++){
     auto&a=x.refs[c];auto&b=y.refs[c];n.fused_moves.push_back({o.p+poff(c,yy,xx,C,H,W),(const uint8_t*)a.p+poff(a.c,yy,xx,a.C,a.H,a.W),(const uint8_t*)b.p+poff(b.c,yy,xx,b.C,b.H,b.W),a.lut,b.lut});
    }
   }n.fused_ready=true;
  }
  const uint8_t*table=n.fused_table.data();
  if(n.fused_fast){
   #pragma omp parallel for schedule(static) num_threads(2) if(o.n>=32768)
   for(size_t i=0;i<n.fused_moves.size();i++){auto&m=n.fused_moves[i];for(int l=0;l<8;l++){uint8_t a=m.left[l],b=m.right[l];if(m.llut)a=m.llut[a];if(m.rlut)b=m.rlut[b];m.dst[l]=table[(unsigned(a)<<8)|b];}}
  }else{
   #pragma omp parallel for schedule(static) num_threads(2) if(o.n>=32768)
   for(int c=0;c<C;c++)for(int yy=0;yy<H;yy++)for(int xx=0;xx<W;xx++){uint8_t a=get(x.refs[c],yy,xx),b=get(y.refs[c],yy,xx);o.p[poff(c,yy,xx,C,H,W)]=table[(unsigned(a)<<8)|b];}
  }
 }
 void materialize_software_debug(){
  if(debug_materialized)return;
  for(int i:schedule)if(nodes[i].software_skip)runnode(nodes[i]);
  debug_materialized=true;
 }
