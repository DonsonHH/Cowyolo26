from pathlib import Path
from datetime import datetime,timezone
import json,urllib.request,base64,hashlib,concurrent.futures
ROOT=Path(__file__).resolve().parents[1];snap=ROOT/'evidence/metadata_snapshots';out=ROOT/'evidence/bound_author_texts';out.mkdir(exist_ok=False)
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
selections={'COLO':('Niche-Lab/COLO','COLO_tree.response',['README.md','.gitmodules','path.py','splitter.py','ms/src/_2_approach.tex']),
 'AutoCattlogger':('VADL-Purdue/AutoCattlogger','AutoCattlogger_tree.response',['README.md','data/readme.md','LICENSE'])}
tasks=[]
for group,(repo,file,paths) in selections.items():
 tree=load(snap/file);assert tree.get('truncated') is not True;mapping={x['path']:x for x in tree['tree']}
 for path in paths:tasks.append((group,repo,path,mapping[path]))
def fetch(task):
 group,repo,path,entry=task;url='https://api.github.com/repos/'+repo+'/git/blobs/'+entry['sha'];row={'group':group,'repo':repo,'path':path,'blob_SHA1':entry['sha'],'url':url,'image_pixels_requested':False}
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'cow-research-source-audit'}),timeout=18) as r:raw=r.read(1024*1024);reply=json.loads(raw)
  assert reply['encoding']=='base64';data=base64.b64decode(reply['content']);assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==entry['sha']
  file=out/(group+'__'+path.replace('/','__'));file.write_bytes(data);row.update({'status':'AUTHOR_TEXT_GIT_BLOB_VERIFIED','file':str(file.resolve()),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 except Exception as e:row.update({'status':'FAILED','error':str(e)[:350]})
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:records=list(pool.map(fetch,tasks))
file=ROOT/'results/author_text_capture_manifest.json';assert not file.exists();file.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'records':records,'new_image_pixels':0,'new_model_forwards':0},indent=2)+'\n',encoding='utf-8')
for r in records:
 print(json.dumps({k:v for k,v in r.items() if k in ['repo','path','status','bytes','error']}))
 if r['status']=='AUTHOR_TEXT_GIT_BLOB_VERIFIED' and r['path'] in ['README.md','.gitmodules','path.py']:print(Path(r['file']).read_text(encoding='utf-8')[:7000])
