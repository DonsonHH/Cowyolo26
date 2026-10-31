from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,tarfile

ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=load(ROOT/'protocol/run_v1.json');e=load(ROOT/'protocol/execution_v1.json');a=load(ROOT/'results/pixel_admission.json')
assert sha(ROOT/'protocol/run_v1.json')==e['protocol_sha256']and len(a['rows'])==90
for file,digest in e['files_sha256'].items():assert sha(ROOT/file)==digest
for row,actual in zip(p['images'],a['rows']):assert sha(ROOT/row['local_relative_file'])==actual['sha256']
files=[ROOT/row['local_relative_file']for row in p['images']]+[ROOT/name for name in ['protocol/run_v1.json','protocol/execution_v1.json','results/acquisition.json','results/pixel_admission.json','results/pre_pixel_review.json','results/pre_pixel_calibration_verification.json','results/cached_calibration_scores.json','results/execution_pre_pixel_gate.json','evidence/first_final_ID_pixel_request_gate.json','evidence/acquisition_rows.jsonl']]+[ROOT/name for name in e['files_sha256']]
archive=ROOT/'final20_input_v1.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz')as tar:
 for path in files:tar.add(path,arcname=path.relative_to(ROOT).as_posix(),recursive=False)
result={'status':'ALL90_AUTHOR_CROPS_AND_FROZEN_EVALUATION_INPUT_BUNDLE_PREPARED','created_UTC':datetime.now(timezone.utc).isoformat(),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files),'protocol_sha256':sha(ROOT/'protocol/run_v1.json'),'execution_sha256':sha(ROOT/'protocol/execution_v1.json'),'JPEG_bytes':sum(row['bytes']for row in a['rows']),'new_model_forwards':0,'final_ID_pixels_now_opened':True,'reservedMar05toMar11_pixels_opened':False};target=ROOT/'evidence/input_bundle.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
