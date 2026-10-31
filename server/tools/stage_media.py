from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from urllib.parse import urljoin,unquote
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor
import json,time,hashlib,sys,os
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026');OUT=ROOT/'catalog';DATA=ROOT/'data';DATA.mkdir(parents=True,exist_ok=True)
proxy=os.environ.get('IDCOO_DOWNLOAD_PROXY')
opener=build_opener(ProxyHandler({'http':proxy,'https':proxy} if proxy else {}))
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,t,a):
  if t=='a':self.links.extend(v for k,v in a if k=='href')
def listing(url,name):
 with opener.open(url,timeout=35) as r:d=r.read(5*1024*1024)
 (OUT/(name+'.html')).write_bytes(d);p=Links();p.feed(d.decode('utf8',errors='replace'))
 links=[urljoin(url,x) for x in p.links if urljoin(url,x).startswith(url)]
 print(json.dumps({'listing':name,'entries':len(links),'examples':links[:5]}),flush=True);return links
def download(url,path,max_bytes=600*1024**2):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():return {'url':url,'path':str(path),'bytes':path.stat().st_size,'status':'existing'}
 part=path.with_suffix(path.suffix+'.partial');t=time.time();sha=hashlib.sha256();offset=part.stat().st_size if part.exists() else 0;total=offset
 headers={'User-Agent':'ID-Coo research'}
 if offset:
  headers['Range']='bytes='+str(offset)+'-'
  with part.open('rb') as f:
   for b in iter(lambda:f.read(1024*1024),b''):sha.update(b)
 with opener.open(Request(url,headers=headers),timeout=45) as r:
  if offset and (r.status!=206 or not r.headers.get('Content-Range','').startswith('bytes '+str(offset)+'-')):raise ValueError('resume range not honored')
  expected=int(r.headers.get('Content-Length',0))+offset
  if expected>max_bytes:return {'url':url,'status':'too_large_for_sample','expected':expected}
  with part.open('ab' if offset else 'wb') as f:
   while True:
    block=r.read(1024*1024)
    if not block:break
    total+=len(block)
    if total>max_bytes:raise ValueError('sample limit')
    f.write(block);sha.update(block)
 if expected and total!=expected:raise ValueError('incomplete transfer')
 part.rename(path);row={'url':url,'path':str(path),'bytes':total,'sha256':sha.hexdigest(),'seconds':round(time.time()-t,2),'status':'downloaded'}
 print(json.dumps(row),flush=True);return row

rows=[];mc='https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/videos/'
for cam in ('camera1','camera2','camera3'):
 links=listing(mc+cam+'/',cam)
 videos=[u for u in links if u.lower().endswith(('.mp4','.avi','.mov','.mkv'))]
 dirs=[u for u in links if u.endswith('/')]
 if not videos and dirs:
  # First-level date directories preserve original acquisition sessions.
  videos=[]
  for j,u in enumerate([dirs[0],dirs[-1]] if len(dirs)>1 else dirs):
   videos.extend(v for v in listing(u,cam+'_date'+str(j)) if v.lower().endswith(('.mp4','.avi','.mov','.mkv')))
 for i,u in enumerate([videos[0],videos[-1]] if len(videos)>1 else videos):
  try:rows.append(download(u,DATA/'multicam_samples'/cam/unquote(u.split('/')[-1])))
  except Exception as e:rows.append({'url':u,'error':type(e).__name__+':'+str(e)[:100]});print(json.dumps(rows[-1]),flush=True)
cv='https://data.bris.ac.uk/datasets/4vnrca7qw1642qlwxjadp87h7/Sub-levels/Identification/Videos/'
seqs=[u for u in listing(cv,'cows2021_sequences') if u.endswith('/')]
chosen=[]
for day in ('2020-03-08','2020-03-09','2020-03-10','2020-03-11'):
 dayseq=[u for u in seqs if day in u]; chosen.extend(([dayseq[0],dayseq[-1]] if len(dayseq)>1 else dayseq))
seq_manifest=[]
for u in chosen:
 name=u.rstrip('/').split('/')[-1];links=listing(u,'seq_'+name)
 media=[v for v in links if v.lower().endswith(('.jpg','.png','.mp4','.avi','.json','.txt','.csv'))]
 seq_manifest.append({'sequence':name,'url':u,'files':media})
 for v in media:
  try:rows.append(download(v,DATA/'cows2021_samples'/name/unquote(v.split('/')[-1]),120*1024**2))
  except Exception as e:rows.append({'url':v,'error':str(e)[:100]})
 (OUT/'staging_manifest.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
(OUT/'sequence_manifest.json').write_text(json.dumps(seq_manifest,indent=2),encoding='utf8')
(OUT/'staging_manifest.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print(json.dumps({'staged_files':len(rows),'downloaded_bytes':sum(r.get('bytes',0) for r in rows),'sequences':len(seq_manifest)}),flush=True)
