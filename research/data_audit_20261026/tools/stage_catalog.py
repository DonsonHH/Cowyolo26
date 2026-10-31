from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from urllib.parse import urljoin
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,time,sys

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026')
OUT=ROOT/'catalog';OUT.mkdir(parents=True,exist_ok=True)
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):
  if tag=='a':self.links.extend(v for k,v in attrs if k=='href')
IDS={'OpenCows2020':'10m32xl88x2b61zlkkgz3fml17','Cows2021':'4vnrca7qw1642qlwxjadp87h7','MultiCamCows2024':'2inu67jru7a6821kkgehxg3cv2'}
def fetch(item):
 name,url=item;op=build_opener(ProxyHandler({}));t=time.time()
 try:
  with op.open(Request(url,headers={'User-Agent':'ID-Coo research dataset audit'}),timeout=35) as r:data=r.read(4*1024*1024);status=r.status
  path=OUT/(name+'.txt');path.write_bytes(data)
  p=Links();p.feed(data.decode('utf8',errors='replace'))
  return {'name':name,'url':url,'status':status,'bytes':len(data),'seconds':round(time.time()-t,2),'sha256':hashlib.sha256(data).hexdigest(),'links':[urljoin(url,x) for x in p.links]}
 except Exception as e:return {'name':name,'url':url,'error':type(e).__name__+': '+str(e)[:180]}
items=[]
for n,id in IDS.items():
 base='https://data.bris.ac.uk/datasets/'+id+'/'
 items.extend([(n+'_index',base),(n+'_readme',base+('ReadMe.txt' if n=='OpenCows2020' else 'readme.txt'))])
with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(fetch,items))
(OUT/'catalog_manifest.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
for r in rows:print(json.dumps(r),flush=True)
