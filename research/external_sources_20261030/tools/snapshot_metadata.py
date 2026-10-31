from pathlib import Path
from datetime import datetime,timezone
import urllib.request,urllib.error,json,hashlib,concurrent.futures,base64
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/metadata_snapshots';OUT.mkdir(parents=True,exist_ok=False)
ENDPOINTS=[
 ('COLO_repo','https://api.github.com/repos/Niche-Lab/COLO'),
 ('COLO_tree','https://api.github.com/repos/Niche-Lab/COLO/git/trees/main?recursive=1'),
 ('COLO_HF_info','https://huggingface.co/api/datasets/Niche-Squad/COLO/revision/main'),
 ('COLO_HF_readme','https://huggingface.co/datasets/Niche-Squad/COLO/raw/main/README.md'),
 ('AutoCattlogger_repo','https://api.github.com/repos/VADL-Purdue/AutoCattlogger'),
 ('AutoCattlogger_tree','https://api.github.com/repos/VADL-Purdue/AutoCattlogger/git/trees/main?recursive=1'),
 ('AutoCattlogger_data_readme','https://raw.githubusercontent.com/VADL-Purdue/AutoCattlogger/main/data/readme.md'),
 ('CattleEyeView_repo','https://api.github.com/repos/AnimalEyeQ/CattleEyeView'),
 ('CattleEyeView_tree','https://api.github.com/repos/AnimalEyeQ/CattleEyeView/git/trees/main?recursive=1'),
 ('CattleEyeView_readme','https://raw.githubusercontent.com/AnimalEyeQ/CattleEyeView/main/README.md'),
 ('predicted_tracks_card','https://huggingface.co/datasets/sakifkhan98/cattle-vision-data/raw/main/README.md')]
def fetch(item):
 name,url=item;row={'name':name,'requested_URL':url,'started_UTC':datetime.now(timezone.utc).isoformat(),'image_pixels_requested':False}
 req=urllib.request.Request(url,headers={'User-Agent':'cow-research-source-audit','Accept':'application/json, text/plain, */*'})
 try:
  with urllib.request.urlopen(req,timeout=18) as response:
   data=response.read(4*1024*1024+1);assert len(data)<=4*1024*1024
   row.update({'status':'RESPONSE_CAPTURED','HTTP_status':response.status,'final_URL':response.url,'content_type':response.headers.get('Content-Type'),'etag':response.headers.get('ETag')})
  f=OUT/(name+'.response');f.write_bytes(data);row.update({'file':str(f.resolve()),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 except Exception as error:row.update({'status':'FAILED_RESPONSE_NOT_CONTENT_PROOF','error_type':type(error).__name__,'error':str(error)[:400]})
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(fetch,ENDPOINTS))
record={'created_UTC':datetime.now(timezone.utc).isoformat(),'status':'METADATA_ENDPOINT_SNAPSHOTS_ATTEMPTED','results':results,'new_image_pixels':0,'new_model_forwards':0,'whole_goal_complete':False}
f=ROOT/'results/metadata_snapshot_manifest.json';f.parent.mkdir(parents=True,exist_ok=True);assert not f.exists();f.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
for r in results:
 summary={k:r.get(k) for k in ['name','status','HTTP_status','bytes','error'] if r.get(k) is not None}
 if r['status']=='RESPONSE_CAPTURED':
  try:
   data=json.loads(Path(r['file']).read_text(encoding='utf-8'))
   if isinstance(data,dict) and 'tree' in data:summary['entries']=len(data['tree']);summary['first_paths']=[x['path'] for x in data['tree'][:8]]
   elif isinstance(data,dict) and 'sha' in data:summary['revision']=data['sha'];summary['siblings']=len(data.get('siblings',[]))
  except Exception:pass
 print(json.dumps(summary),flush=True)
