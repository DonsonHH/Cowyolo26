"""Acquire only90 sealed public files after code freeze; durable exact-file journal."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import concurrent.futures,hashlib,io,json,os,time,urllib.request,urllib.error,zlib
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n')
p=load(ROOT/'protocol/run_v1.json');e=load(ROOT/'protocol/execution_v1.json');assert sha(ROOT/'protocol/run_v1.json')==e['protocol_sha256']
for file,digest in e['files_sha256'].items():assert sha(ROOT/file)==digest
assert not(ROOT/'input').exists()and not(ROOT/'results/acquisition.json').exists()
(ROOT/'input/images').mkdir(parents=True,exist_ok=False);(ROOT/'evidence').mkdir(exist_ok=True)
save(ROOT/'evidence/first_final_ID_pixel_request_gate.json',{'status':'EXECUTION_CODE_MODELS_THRESHOLDS_AND90_METADATA_CHECKED_BEFORE_FIRST_FINAL_ID_REQUEST','created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':e['protocol_sha256'],'execution_sha256':sha(ROOT/'protocol/execution_v1.json'),'new_model_forwards':0})

def acquire(item):
 index,row=item;record={'index':index,'publisher_identity':row['publisher_identity'],'purpose':row['purpose'],'date':row['date'],'local_relative_file':row['local_relative_file'],'attempts':[]}
 url=p['source_base_URL']+row['publisher_identity']+'/'+row['file_name']
 try:
  for attempt in range(2):
   try:
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({'http':'http://127.0.0.1:7897','https':'http://127.0.0.1:7897'}))
    with opener.open(urllib.request.Request(url,headers={'User-Agent':'cow-research-final90-sealed-v1'}),timeout=25)as response:
     raw=response.read(5000000);assert response.status==200 and len(raw)<5000000;record['attempts'].append({'attempt':attempt+1,'status':'SUCCESS','HTTP_status':response.status,'URL':response.url})
    break
   except(urllib.error.URLError,TimeoutError)as error:
    record['attempts'].append({'attempt':attempt+1,'status':'NETWORK_ERROR','error':repr(error)[:300]})
    if isinstance(error,urllib.error.HTTPError)or attempt==1:raise
  assert len(raw)==row['zip_entry']['uncompressed_size']and zlib.crc32(raw)&0xffffffff==row['zip_entry']['CRC32']
  with Image.open(io.BytesIO(raw))as image:image.load();rgb=image.convert('RGB')
  assert rgb.width>0 and rgb.height>0;path=ROOT/row['local_relative_file'];assert path.resolve().is_relative_to((ROOT/'input/images').resolve())and not path.exists();path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
  pixel=hashlib.sha256(rgb.width.to_bytes(4,'big')+rgb.height.to_bytes(4,'big')+rgb.tobytes()).hexdigest()
  record.update({'status':'FINAL_ID_AUTHOR_JPEG_CRC_RGB_PASS','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'WH':list(rgb.size),'canonical_pixel_sha256':pixel})
 except BaseException as error:record.update({'status':'FAILED_NO_ID_OR_IMAGE_REPLACEMENT','error':repr(error)[:500]})
 return record

records=[]
with(ROOT/'evidence/acquisition_rows.jsonl').open('x')as journal,concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:
 for record in pool.map(acquire,enumerate(p['images'])):
  records.append(record);journal.write(json.dumps(record)+'\n');journal.flush();os.fsync(journal.fileno())
  if len(records)%15==0:print(json.dumps({'received_rows':len(records),'successful':sum(r['status']=='FINAL_ID_AUTHOR_JPEG_CRC_RGB_PASS'for r in records),'new_model_forwards':0}),flush=True)
save(ROOT/'results/acquisition.json',{'status':'FINAL90_AUTHOR_FILE_ACQUISITION_FINISHED','created_UTC':datetime.now(timezone.utc).isoformat(),'records':records,'failed':sum(r['status']!='FINAL_ID_AUTHOR_JPEG_CRC_RGB_PASS'for r in records),'protocol_sha256':e['protocol_sha256'],'new_model_forwards':0,'proxy_or_node_configuration_changed':False,'whole_goal_complete':False})
assert len(records)==90 and all(r['status']=='FINAL_ID_AUTHOR_JPEG_CRC_RGB_PASS'for r in records)
old=load(PROJECT/'cows2021_identity_eval_20261030/results/pixel_admission.json');train=load(PROJECT/'identity_domain_adapt_20261030/results/acquisition.json')
prior={r['canonical_pixel_sha256']for r in old['rows']}|{r['canonical_pixel_sha256']for r in train['records']};pixels=defaultdict(list)
for r in records:assert r['canonical_pixel_sha256']not in prior;pixels[r['canonical_pixel_sha256']].append(r['index'])
assert not any(len(v)>1 for v in pixels.values())
save(ROOT/'results/pixel_admission.json',{'status':'ALL90_FIXED_FINAL_ID_CROPS_CRC_RGB_AND_NO_EXACT_PRIOR_PIXEL_OVERLAP_PASS','created_UTC':datetime.now(timezone.utc).isoformat(),'rows':records,'prior540_development_and457_training_exact_pixel_overlap':0,'within90_exact_duplicates':0,'new_model_forwards':0,'final20_ID_pixels_opened':True,'reservedMar05toMar11_pixels_opened':False,'whole_goal_complete':False})
print(json.dumps({'admitted_images':90,'source_JPEG_bytes':sum(r['bytes']for r in records),'new_model_forwards':0}),flush=True)
