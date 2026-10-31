from pathlib import Path
from datetime import datetime,timezone
import urllib.request,json,hashlib,concurrent.futures
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'evidence/existing_local_gateway';out.mkdir(exist_ok=False)
tasks=[('HF_info','https://huggingface.co/api/datasets/Niche-Squad/COLO/revision/main','GET',None),
 ('HF_readme','https://huggingface.co/datasets/Niche-Squad/COLO/raw/main/README.md','GET',None),
 ('HF_splits','https://datasets-server.huggingface.co/splits?dataset=Niche-Squad%2FCOLO','GET',None),
 ('Auto_samples1','https://app.box.com/shared/static/rih8q2jc7dtgi9yge17wfz84y15rqkez','HEAD',None),
 ('Auto_samples2','https://app.box.com/shared/static/aagwjs8b42q11xc6b6l75ccgk47s8tl4','HEAD',None)]
def fetch(task):
 name,url,method,unused=task;row={'name':name,'requested_public_URL':url,'request_gateway':'existing127.0.0.1:7897','global_proxy_or_node_configuration_changed':False}
 try:
  opener=urllib.request.build_opener(urllib.request.ProxyHandler({'http':'http://127.0.0.1:7897','https':'http://127.0.0.1:7897'}))
  with opener.open(urllib.request.Request(url,method=method,headers={'User-Agent':'cow-research-source-audit'}),timeout=18) as r:
   row.update({'status':'RESPONSE_CAPTURED_VIA_EXISTING_LOCAL_GATEWAY','HTTP_status':r.status,'final_host':r.url.split('/')[2],'content_type':r.headers.get('Content-Type'),'content_length':r.headers.get('Content-Length'),'accept_ranges':r.headers.get('Accept-Ranges'),'content_disposition':r.headers.get('Content-Disposition')})
   if method=='GET':
    data=r.read(2*1024*1024+1);assert len(data)<=2*1024*1024;f=out/(name+'.response');f.write_bytes(data);row.update({'file':str(f.resolve()),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 except Exception as e:row.update({'status':'FAILED_ACCESS_NOT_CONTENT_PROOF','error':str(e)[:350]})
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:records=list(pool.map(fetch,tasks))
file=ROOT/'results/existing_local_gateway_probe.json';assert not file.exists();file.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'records':records,'new_image_pixels':0,'new_model_forwards':0,'new_listener_proxy_selector_or_node_changes':False},indent=2)+'\n',encoding='utf-8')
for r in records:print(json.dumps({k:v for k,v in r.items() if k not in ['requested_public_URL','file']}),flush=True)
