from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from urllib.parse import urljoin
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
import json,re,hashlib
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/phase2');OUT=ROOT/'catalog';OUT.mkdir(parents=True,exist_ok=True)
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,t,a):
  if t=='a':self.links.extend(v for k,v in a if k=='href')
URLS={
 'mendeley_page':'https://data.mendeley.com/datasets/dk54zg67dd/1',
 'mendeley_files':'https://data.mendeley.com/public-api/datasets/dk54zg67dd/versions/1/files',
 'mendeley_public':'https://api.mendeley.com/datasets/dk54zg67dd/versions/1?view=all',
 'mc_camera2':'https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/videos/camera2/',
 'mc_camera3':'https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/videos/camera3/'
}
def fetch(item):
 name,u=item
 try:
  op=build_opener(ProxyHandler({}))
  with op.open(Request(u,headers={'User-Agent':'Mozilla/5.0 ID-Coo public research','Accept':'application/json,text/html,*/*'}),timeout=25) as r:d=r.read(8*1024**2);status=r.status
  (OUT/(name+'.txt')).write_bytes(d);p=Links();p.feed(d.decode('utf8',errors='replace'))
  links=[urljoin(u,l) for l in p.links]
  out={'name':name,'url':u,'status':status,'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest(),'links':links[:30]}
  if name=='mendeley_page':
   text=d.decode('utf8',errors='replace')
   out['download_related_strings']=re.findall(r'.{0,80}(?:download_url|downloadUrl|public-api|api/datasets|files|__PRELOADED|__NEXT_DATA__).{0,160}',text)[:30]
  if name=='mendeley_files':out['json_preview']=d.decode()[:3000]
  return out
 except Exception as e:return {'name':name,'url':u,'error':type(e).__name__+': '+str(e)[:150]}
with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(fetch,URLS.items()))
(OUT/'initial_sources.json').write_text(json.dumps(results,indent=2),encoding='utf8')
for r in results:print(json.dumps(r),flush=True)
