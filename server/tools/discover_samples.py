from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from urllib.parse import urljoin,unquote
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
import json,time,hashlib
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026'); OUT=ROOT/'catalog'
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,t,a):
  if t=='a':self.links.extend(v for k,v in a if k=='href')
def fetch(n,u):
 try:
  op=build_opener(ProxyHandler({}));t=time.time()
  with op.open(Request(u,headers={'User-Agent':'ID-Coo Research'}),timeout=25) as r:d=r.read(3*1024*1024)
  (OUT/(n+'.html')).write_bytes(d);p=Links();p.feed(d.decode('utf8',errors='replace'))
  return {'name':n,'url':u,'bytes':len(d),'links':[urljoin(u,x) for x in p.links]}
 except Exception as e:return {'name':n,'error':type(e).__name__+':'+str(e)[:100]}
base='https://data.bris.ac.uk/datasets/'
todo=[('Cows2021_sub',base+'4vnrca7qw1642qlwxjadp87h7/Sub-levels/'),('MultiCam_root',base+'2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/')]
allrows=[]
for depth in range(4):
 if not todo:break
 with ThreadPoolExecutor(max_workers=3) as pool:rows=list(pool.map(lambda x:fetch(*x),todo))
 todo=[]
 for row in rows:
  allrows.append(row);print(json.dumps(row),flush=True)
  for url in row.get('links',[]):
   suffix=unquote(url.rstrip('/').split('/')[-1])
   if url.startswith(row.get('url','')) and url.endswith('/') and suffix.lower() in ('identification','videos','video','test','train','detection_and_localisation'):
    todo.append((row['name']+'_'+suffix,url))
(OUT/'discovery.json').write_text(json.dumps(allrows,indent=2),encoding='utf8')
url=base+'10m32xl88x2b61zlkkgz3fml17/10m32xl88x2b61zlkkgz3fml17.zip'
try:
 op=build_opener(ProxyHandler({})); t=time.time()
 with op.open(Request(url,headers={'Range':'bytes=0-8388607'}),timeout=25) as r:
  d=r.read(8388608); hdr=dict(r.headers);status=r.status
 print(json.dumps({'speed_probe_bytes':len(d),'seconds':round(time.time()-t,2),'status':status,'header_type':hdr.get('Content-Type'),'content_range':hdr.get('Content-Range'),'magic':d[:4].hex()}),flush=True)
except Exception as e:print(json.dumps({'probe_error':str(e)[:160]}),flush=True)
