from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,urllib.request,urllib.error,concurrent.futures
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'evidence/data_endpoint_probes';out.mkdir(exist_ok=False)
tasks=[
 ('COLO_release','https://api.github.com/repos/Niche-Lab/COLO/releases/tags/v1.0.0','GET'),
 ('AutoCattlogger_commit','https://api.github.com/repos/VADL-Purdue/AutoCattlogger/commits/main','GET'),
 ('COLO_commit','https://api.github.com/repos/Niche-Lab/COLO/commits/main','GET'),
 ('Auto_samples1','https://app.box.com/shared/static/rih8q2jc7dtgi9yge17wfz84y15rqkez','HEAD'),
 ('Auto_samples2','https://app.box.com/shared/static/aagwjs8b42q11xc6b6l75ccgk47s8tl4','HEAD'),
 ('Auto_detection_test','https://app.box.com/shared/static/dc9de5i9kh8j1jcq1atliog972r93yhp','HEAD'),
 ('CattleEyeView_form','https://docs.google.com/forms/d/e/1FAIpQLSdLffqnj7sC7qXHMUpcu_E7GZLDYGaEMutCHbr3v_kghlmP3w/viewform?usp=send_form','GET')]
def fetch(task):
 name,url,method=task;r={'name':name,'method':method,'requested_public_URL':url,'started_UTC':datetime.now(timezone.utc).isoformat(),'image_pixels_requested':False,'form_submitted':False}
 try:
  request=urllib.request.Request(url,method=method,headers={'User-Agent':'cow-research-source-audit'})
  with urllib.request.urlopen(request,timeout=15) as response:
   r.update({'status':'RESPONSE_CAPTURED','HTTP_status':response.status,'final_URL_without_query':response.url.split('?')[0],
    'content_type':response.headers.get('Content-Type'),'content_length':response.headers.get('Content-Length'),'accept_ranges':response.headers.get('Accept-Ranges'),'content_disposition':response.headers.get('Content-Disposition')})
   if method=='GET':
    data=response.read(2*1024*1024+1);assert len(data)<=2*1024*1024
    f=out/(name+'.response');f.write_bytes(data);r.update({'file':str(f.resolve()),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 except Exception as e:r.update({'status':'FAILED_ACCESS_NOT_CONTENT_PROOF','error':str(e)[:400]})
 return r
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:records=list(pool.map(fetch,tasks))
f=ROOT/'results/data_endpoint_probe_manifest.json';assert not f.exists();f.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'records':records,'new_image_pixels':0,'new_model_forwards':0},indent=2)+'\n',encoding='utf-8')
for r in records:
 summary={k:v for k,v in r.items() if k in ['name','status','HTTP_status','content_type','content_length','accept_ranges','content_disposition','error']}
 if r['name']=='COLO_release' and r['status']=='RESPONSE_CAPTURED':
  d=json.loads(Path(r['file']).read_text(encoding='utf-8'));summary.update({'tag':d['tag_name'],'published_at':d['published_at'],'assets':[{'name':a['name'],'size':a['size'],'URL':a['browser_download_url']} for a in d.get('assets',[])]})
 print(json.dumps(summary),flush=True)
