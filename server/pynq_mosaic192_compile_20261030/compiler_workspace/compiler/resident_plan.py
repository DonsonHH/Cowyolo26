"""Compile bounded, lossless resident pairs over the frozen logical O7 graph."""
import argparse,collections,hashlib,json,pathlib,struct,heapq

def make(root,size,selection='adjacent',capacity=131072):
 root=pathlib.Path(root);P=root/f'program_r{size}';g=json.loads((P/'program.json').read_text());ns=g['nodes'];sh=g['shapes'];use=collections.defaultdict(list)
 for i,n in enumerate(ns):
  for x in n['inputs']:use[x].append(i)
 candidates=[];rejections=[]
 for i,a in enumerate(ns):
  if a['op']!='QuantConv':continue
  out=a['outputs'][0];cons=use[out]
  if len(cons)!=1:continue
  j=cons[0];b=ns[j]
  if b['op']!='QuantConv' or b['inputs'][0]!=out:continue
  N,C,H,W=sh[out][0];nb=N*C*H*W
  valid=nb<=capacity and N==1 and C%8==0 and all(v<=256 for v in (H,W))
  valid=valid and (selection!='adjacent' or j==i+1)
  for z in (a,b):
   sid,ci,co,k,*_=z['attrs'];valid=valid and ci<=512 and ((min(co,32)+15)//16)*((ci+7)//8)*k*k<=512
  row=dict(producer_node=i,consumer_node=j,producer_sid=a['attrs'][0],consumer_sid=b['attrs'][0],tensor_name=out,tensor_id=g['names'].index(out),tensor_bytes=nb,shape=[C,H,W],adjacent=j==i+1)
  (candidates if valid else rejections).append(row)
 # Prefer high byte-removal candidates while preventing pairs sharing an op.
 # For the adjacent starter, deterministic graph order keeps the original schedule.
 if selection!='adjacent':candidates.sort(key=lambda r:(-r['tensor_bytes'],r['producer_node']))
 chosen=[];used=set()
 for c in candidates:
  if c['producer_node'] not in used and c['consumer_node'] not in used:
   chosen.append(c);used.update((c['producer_node'],c['consumer_node']))
 chosen.sort(key=lambda r:r['producer_node'])
 # Contracting selected direct single-consumer edges must leave a DAG.
 owner={i:i for i in range(len(ns))}
 for c in chosen:owner[c['consumer_node']]=c['producer_node']
 pred={x:i for i,n in enumerate(ns) for x in n['outputs']};edges=collections.defaultdict(set);indeg=collections.Counter()
 groups=set(owner.values())
 for i,n in enumerate(ns):
  for x in n['inputs']:
   if x not in pred:continue
   a,b=owner[pred[x]],owner[i]
   if a!=b and b not in edges[a]:edges[a].add(b);indeg[b]+=1
 ready=[i for i in groups if not indeg[i]];heapq.heapify(ready);schedule=[]
 while ready:
  i=heapq.heappop(ready);schedule.append(i)
  for j in sorted(edges[i]):
   indeg[j]-=1
   if not indeg[j]:heapq.heappush(ready,j)
 assert len(schedule)==len(groups),'contraction dependency cycle'
 pairmap={r['producer_node']:r['consumer_node'] for r in chosen};expanded=[]
 for i in schedule:expanded.append(i);expanded.extend([pairmap[i]] if i in pairmap else [])
 assert sorted(expanded)==list(range(len(ns)))
 positions={i:p for p,i in enumerate(expanded)}
 for i,n in enumerate(ns):
  for x in n['inputs']:
   if x in pred:assert positions[pred[x]]<positions[i],('illegal reorder',x)
 return dict(format='O8RP',version=1,core='0x80001',capacity_bytes=capacity,size=size,graph_sha256=hashlib.sha256((P/'graph.bin').read_bytes()).hexdigest(),selection=selection,logical_nodes=len(ns),pairs=chosen,excluded=rejections,schedule=expanded,baseline_dense_DMA_calls=94,resident_DMA_calls=94-len(chosen),proof='All logical nodes preserved once; all tensor dependencies precede consumers; frozen graph/weights unchanged')

def write(plan,out):
 out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=False)
 (out/'resident_plan.json').write_text(json.dumps(plan,indent=2))
 b=struct.pack('<8I',0x3852504f,1,plan['capacity_bytes'],int(plan['core'],16),plan['logical_nodes'],len(plan['pairs']),len(plan['schedule']),0)+bytes.fromhex(plan['graph_sha256'])
 for r in plan['pairs']:b+=struct.pack('<8I',r['producer_node'],r['consumer_node'],r['tensor_id'],r['tensor_bytes'],*r['shape'],r['tensor_id']+1)
 b+=struct.pack('<%dI'%len(plan['schedule']),*plan['schedule'])
 (out/'resident_plan.bin').write_bytes(b)
 return hashlib.sha256(b).hexdigest()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[1]);p.add_argument('--size',type=int,required=True);p.add_argument('--selection',choices=['adjacent','all'],default='adjacent');p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();plan=make(a.root,a.size,a.selection);sha=write(plan,a.output);print('O8_PLAN_PASS',a.size,len(plan['pairs']),plan['resident_DMA_calls'],sha)
