from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
from html.parser import HTMLParser
import json,time,hashlib
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026');OUT=ROOT/'catalog';DATA=ROOT/'data/cows2021_samples'
opener=build_opener(ProxyHandler({'http':'http://127.0.0.1:27831','https':'http://127.0.0.1:27831'}))
base='https://data.bris.ac.uk/datasets/4vnrca7qw1642qlwxjadp87h7/Sub-levels/Identification/Videos/'
rows=json.loads((OUT/'discovery.json').read_text());seqs=next(r['links'] for r in rows if r['name'].endswith('_Videos'))
selected=[]
for day in ('2020-03-08','2020-03-09','2020-03-10','2020-03-11'):
 arr=[u for u in seqs if u.startswith(base) and day in u and u.endswith('/')]
 selected.extend(([arr[0],arr[len(arr)//2]] if len(arr)>1 else arr))
def fetch(u):
 url=u+'RGB.avi';name=u.rstrip('/').split('/')[-1];p=DATA/name/'RGB.avi';p.parent.mkdir(parents=True,exist_ok=True);t=time.time()
 try:
  with opener.open(url,timeout=40) as r:
   expected=int(r.headers.get('Content-Length',0))
   if expected>150*1024**2:return {'sequence':name,'status':'over_sample_limit','bytes':expected}
   part=p.with_suffix('.avi.partial');sha=hashlib.sha256();count=0
   with part.open('wb') as f:
    while b:=r.read(1024*1024):f.write(b);sha.update(b);count+=len(b)
  if expected and expected!=count:raise ValueError('size mismatch')
  part.rename(p);out={'sequence':name,'url':url,'path':str(p),'bytes':count,'sha256':sha.hexdigest(),'seconds':round(time.time()-t,2),'status':'downloaded'}
 except Exception as e:out={'sequence':name,'error':type(e).__name__+':'+str(e)[:130]}
 print(json.dumps(out),flush=True);return out
with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(fetch,selected))
(OUT/'cows2021_priority_manifest.json').write_text(json.dumps(results,indent=2),encoding='utf8')
