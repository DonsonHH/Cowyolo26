"""Recover absent acquisition process from350 durable rows; only missing files."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import concurrent.futures,hashlib,io,json,os,urllib.request,urllib.error,zlib
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
plan=json.loads((ROOT/'protocol/run_v1.json').read_text())
prior_path=ROOT/'evidence/acquisition_rows.jsonl'
prior=[json.loads(line) for line in prior_path.read_text().splitlines()]
assert len(prior)==350 and all(row['status']=='NEW_TRAIN_JPEG_CRC_RGB_AND_PRIOR_PIXEL_OVERLAP_PASS' for row in prior)
assert not(ROOT/'results/acquisition.json').exists()
original539={row['index']:row for row in prior}
assert set(original539)==set(range(350))
old1=json.loads((PROJECT/'cows2021_identity_eval_20261030/results/pixel_admission.json').read_text())
old2=json.loads((PROJECT/'identity_training_20261026/delivery/results/input_audit/manifest.json').read_text())
oldpixels={row['canonical_pixel_sha256'] for row in old1['rows']}|{row['pixel_sha256'] for row in old2}
note={'created_UTC':datetime.now(timezone.utc).isoformat(),'previous_handle35954_missing':True,'matching_Win32_python_process_absent':True,
      'preserved_JPEGs':350,'durable_original_journal_rows':350,'actual_exit_cause_not_observed':True,'resume_only_missing107':True,'new_model_forwards':0}
(ROOT/'evidence/download_resume_reason.json').write_text(json.dumps(note,indent=2)+'\n')


def process(item):
 index,row=item;path=ROOT/row['relative_file'];record={'index':index,'relative_file':row['relative_file'],'identity':row['identity'],'day':row['day'],'attempts':[]}
 if index in original539:
  record=original539[index];raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==record['sha256']
 else:
  assert not path.exists()
  for attempt in range(2):
   try:
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({'http':'http://127.0.0.1:7897','https':'http://127.0.0.1:7897'}))
    with opener.open(urllib.request.Request(row['URL'],headers={'User-Agent':'cow-research-same457-missing-only'}),timeout=25) as response:
     raw=response.read(5000000);assert response.status==200 and len(raw)<5000000
     record['attempts'].append({'attempt':attempt+1,'status':'SUCCESS','HTTP_status':response.status,'URL':response.url})
    break
   except(urllib.error.URLError,TimeoutError) as error:
    record['attempts'].append({'attempt':attempt+1,'status':'NETWORK_ERROR','error':repr(error)[:350]})
    if isinstance(error,urllib.error.HTTPError) or attempt==1:return {**record,'status':'FAILED_NO_IMAGE_REPLACEMENT'}
  path.parent.mkdir(parents=True,exist_ok=True)
  assert len(raw)==row['zip_entry']['uncompressed_size'] and zlib.crc32(raw)&0xffffffff==row['zip_entry']['CRC32']
  path.write_bytes(raw)
 assert len(raw)==row['zip_entry']['uncompressed_size'] and zlib.crc32(raw)&0xffffffff==row['zip_entry']['CRC32']
 with Image.open(io.BytesIO(raw)) as image:image.load();rgb=image.convert('RGB')
 pixel=hashlib.sha256(rgb.width.to_bytes(4,'big')+rgb.height.to_bytes(4,'big')+rgb.tobytes()).hexdigest();assert pixel not in oldpixels
 if index in original539:assert record['canonical_pixel_sha256']==pixel
 return {**record,'status':'NEW_TRAIN_JPEG_CRC_RGB_AND_PRIOR_PIXEL_OVERLAP_PASS','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
         'WH':list(rgb.size),'canonical_pixel_sha256':pixel,'original_complete_file_reused':index in original539}


records=[]
with(ROOT/'evidence/acquisition_resume_rows.jsonl').open('x',encoding='utf-8') as journal,concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 for row in pool.map(process,enumerate(plan['Cows_training_images'])):
  records.append(row);journal.write(json.dumps(row)+'\n');journal.flush();os.fsync(journal.fileno())
  if len(records)%60==0:print(json.dumps({'rows_verified':len(records),'new_model_forwards':0}),flush=True)
failures=[row for row in records if row['status']!='NEW_TRAIN_JPEG_CRC_RGB_AND_PRIOR_PIXEL_OVERLAP_PASS'];pixels=defaultdict(list)
for row in records:
 if 'canonical_pixel_sha256'in row:pixels[row['canonical_pixel_sha256']].append(row['index'])
result={'status':'ALL457_TRAIN_JPEGS_COMPLETE350_REUSED107_MISSING_RECOVERED','created_UTC':datetime.now(timezone.utc).isoformat(),
        'protocol_sha256':hashlib.sha256((ROOT/'protocol/run_v1.json').read_bytes()).hexdigest(),'records':records,'failed_images':len(failures),
        'same_pixel_duplicate_groups':[indices for indices in pixels.values() if len(indices)>1],
        'prior540_and750_exact_pixel_overlap':0 if not failures else None,'future20_ID_pixels_opened':False,
        'new_model_forwards':0,'proxy_or_node_settings_changed':False,'whole_goal_complete':False}
p=ROOT/'results/acquisition.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':result['status'],'images':len(records),'failures':len(failures),'JPEG_bytes':sum(row.get('bytes',0)for row in records),'new_model_forwards':0}),flush=True)
assert len(records)==457 and not failures and not result['same_pixel_duplicate_groups']
