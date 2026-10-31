set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
cd /share/home/renly/projects/idcoo_research_20261026/external_sources_20261030
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import urllib.request,socket,json,hashlib,concurrent.futures
root=Path.cwd();out=root/'existing_loopback_responses';out.mkdir(exist_ok=False)
ports=[];health=[]
for port in [2080,27831]:
 try:s=socket.create_connection(('127.0.0.1',port),timeout=1);s.close();ports.append(port)
 except OSError:pass
selected=None
for port in ports:
 try:
  op=urllib.request.build_opener(urllib.request.ProxyHandler({'http':'http://127.0.0.1:'+str(port),'https':'http://127.0.0.1:'+str(port)}))
  with op.open('https://ipinfo.io/json',timeout=10) as r:d=json.loads(r.read(8192));country=d.get('country')
  health.append({'existing_port':port,'HTTPS_succeeded':True,'country_only':country})
  if country=='SG' and selected is None:selected=port
 except Exception as e:health.append({'existing_port':port,'HTTPS_succeeded':False,'error':str(e)[:250]})
tasks=[('HF_info','https://huggingface.co/api/datasets/Niche-Squad/COLO/revision/main','GET',None),
 ('HF_readme','https://huggingface.co/datasets/Niche-Squad/COLO/raw/main/README.md','GET',None),
 ('COLO_tail','https://github.com/Niche-Lab/COLO/releases/download/v1.0.0/COLO_COCO.zip','GET','bytes=420477515-420543071'),
 ('Auto_samples1','https://app.box.com/shared/static/rih8q2jc7dtgi9yge17wfz84y15rqkez','HEAD',None),
 ('Auto_samples2','https://app.box.com/shared/static/aagwjs8b42q11xc6b6l75ccgk47s8tl4','HEAD',None)]
def fetch(task):
 name,url,method,ranged=task;row={'name':name,'requested_public_URL':url}
 if selected is None:return {**row,'status':'NOT_ATTEMPTED_NO_EXISTING_SG_ROUTE'}
 try:
  op=urllib.request.build_opener(urllib.request.ProxyHandler({'http':'http://127.0.0.1:'+str(selected),'https':'http://127.0.0.1:'+str(selected)}));headers={'User-Agent':'cow-research-source-audit'}
  if ranged:headers['Range']=ranged
  with op.open(urllib.request.Request(url,method=method,headers=headers),timeout=15) as r:
   row.update({'status':'CAPTURED_VIA_UNMODIFIED_EXISTING_LOOPBACK','HTTP_status':r.status,'content_type':r.headers.get('Content-Type'),'content_length':r.headers.get('Content-Length'),'content_range':r.headers.get('Content-Range'),'accept_ranges':r.headers.get('Accept-Ranges'),'etag':r.headers.get('ETag'),'final_host':r.url.split('/')[2]})
   if method=='GET':
    limit=65557 if ranged else 2*1024*1024
    if ranged and r.status!=206:raise RuntimeError('Range_not_honored')
    data=r.read(limit+1);assert len(data)<=limit;f=out/(name+'.response');f.write_bytes(data);row.update({'file':str(f),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 except Exception as e:row.update({'status':'FAILED_ACCESS_NOT_CONTENT_PROOF','error':str(e)[:350]})
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(fetch,tasks))
report={'created_UTC':datetime.now(timezone.utc).isoformat(),'health':health,'selected_existing_port_for_requests':selected,
 'no_proxy_process_started_or_selected_or_reconfigured':True,'GLOBAL_or_provider_selector_not_changed':True,'controller_or_subscription_secrets_not_read':True,
 'proxy_group_selection_not_inspected_or_claimed':True,'records':records,'image_pixels_decoded':0,'new_model_forwards':0}
f=root/'existing_loopback_probe.json';f.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
PY
