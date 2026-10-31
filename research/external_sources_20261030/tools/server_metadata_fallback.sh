set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
id -un
hostname
sinfo -o '%P|%a|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
test ! -e /share/home/renly/projects/idcoo_research_20261026/external_sources_20261030
mkdir /share/home/renly/projects/idcoo_research_20261026/external_sources_20261030
cd /share/home/renly/projects/idcoo_research_20261026/external_sources_20261030
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,urllib.request,hashlib,concurrent.futures
root=Path.cwd();out=root/'endpoint_responses';out.mkdir(exist_ok=False)
tasks=[('HF_info','https://huggingface.co/api/datasets/Niche-Squad/COLO/revision/main','GET',None),
 ('HF_readme','https://huggingface.co/datasets/Niche-Squad/COLO/raw/main/README.md','GET',None),
 ('HF_splits','https://datasets-server.huggingface.co/splits?dataset=Niche-Squad%2FCOLO','GET',None),
 ('COLO_zip_tail','https://github.com/Niche-Lab/COLO/releases/download/v1.0.0/COLO_COCO.zip','GET','bytes=420477515-420543071'),
 ('Auto_samples1','https://app.box.com/shared/static/rih8q2jc7dtgi9yge17wfz84y15rqkez','HEAD',None),
 ('Auto_samples2','https://app.box.com/shared/static/aagwjs8b42q11xc6b6l75ccgk47s8tl4','HEAD',None)]
def probe(task):
 name,url,method,requested_range=task;row={'name':name,'requested_public_URL':url,'route':'existing_environment_default_no_configuration_change','new_image_pixels':0}
 try:
  headers={'User-Agent':'cow-research-source-audit'}
  if requested_range:headers['Range']=requested_range
  with urllib.request.urlopen(urllib.request.Request(url,method=method,headers=headers),timeout=15) as r:
   row.update({'status':'RESPONSE_CAPTURED','HTTP_status':r.status,'final_host':r.url.split('/')[2],'content_type':r.headers.get('Content-Type'),'content_length':r.headers.get('Content-Length'),'content_range':r.headers.get('Content-Range'),'accept_ranges':r.headers.get('Accept-Ranges'),'etag':r.headers.get('ETag')})
   if method=='GET':
    limit=65557 if requested_range else 2*1024*1024
    if requested_range and r.status!=206:raise RuntimeError('Range_not_honored')
    data=r.read(limit+1);assert len(data)<=limit
    f=out/(name+'.response');f.write_bytes(data);row.update({'file':str(f),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
 except Exception as e:row.update({'status':'FAILED_ACCESS_NOT_CONTENT_PROOF','error':str(e)[:350]})
 return row
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(probe,tasks))
p=root/'server_metadata_manifest.json';p.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'records':records,'sustained_compute_or_model_forward':False,'whole_goal_complete':False},indent=2)+'\n')
for row in records:print(json.dumps({k:v for k,v in row.items() if k!='requested_public_URL'}),flush=True)
PY
