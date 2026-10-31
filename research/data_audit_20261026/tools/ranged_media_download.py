from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from concurrent.futures import ThreadPoolExecutor,as_completed
import argparse,json,time,hashlib,shutil

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026')
def dl(url,path,workers=8):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():return {'path':str(path),'bytes':path.stat().st_size,'status':'existing'}
 proxy={'http':'http://127.0.0.1:27831','https':'http://127.0.0.1:27831'}
 def op():return build_opener(ProxyHandler(proxy))
 with op().open(Request(url,method='HEAD'),timeout=30) as r:size=int(r.headers['Content-Length'])
 part=path.with_suffix(path.suffix+'.partial');prefix=part.stat().st_size if part.exists() else 0
 chunks=path.parent/(path.name+'.download_chunks');chunks.mkdir(exist_ok=True);bs=1024*1024;t=time.time()
 spans=[(start,min(start+bs,size)-1) for start in range(prefix,size,bs)]
 print(json.dumps({'start':str(path),'expected_bytes':size,'existing_prefix':prefix,'chunks':len(spans),'workers':workers}),flush=True)
 def fetch(span):
  start,end=span;p=chunks/f'{start:012d}-{end:012d}.bin'
  if p.exists() and p.stat().st_size==end-start+1:return span
  for attempt in range(3):
   try:
    with op().open(Request(url,headers={'Range':f'bytes={start}-{end}','User-Agent':'ID-Coo research'}),timeout=45) as r:
     if r.status!=206 or not r.headers.get('Content-Range','').startswith(f'bytes {start}-{end}/'):raise ValueError('server ignored range')
     data=r.read(end-start+2)
    if len(data)!=end-start+1:raise ValueError('short response')
    p.write_bytes(data);return span
   except Exception:
    if attempt==2:raise
    time.sleep(1+attempt)
 completed=0
 with ThreadPoolExecutor(max_workers=workers) as pool:
  for future in as_completed([pool.submit(fetch,span) for span in spans]):
   future.result();completed+=1
   if completed%10==0:print(json.dumps({'path':str(path),'chunks_done':completed,'chunks_total':len(spans),'elapsed_s':round(time.time()-t,1)}),flush=True)
 with part.open('ab') as f:
  for start,end in spans:
   with (chunks/f'{start:012d}-{end:012d}.bin').open('rb') as source:shutil.copyfileobj(source,f)
 if part.stat().st_size!=size:raise ValueError('assembled size mismatch')
 sha=hashlib.sha256()
 with part.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):sha.update(b)
 part.rename(path);row={'url':url,'path':str(path),'bytes':size,'sha256':sha.hexdigest(),'seconds':round(time.time()-t,2),'status':'downloaded','transport':'verified HTTP ranges via isolated US3'}
 (path.parent/(path.name+'.manifest.json')).write_text(json.dumps(row,indent=2),encoding='utf8');print(json.dumps(row),flush=True);return row
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('url');p.add_argument('path');p.add_argument('--workers',type=int,default=8);a=p.parse_args();dl(a.url,a.path,a.workers)
