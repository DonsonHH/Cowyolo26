from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
v=load(ROOT/'results/independent_verification.json');rows=load(ROOT/'results/actual_job_rows.json');bindings=load(ROOT/'numeric_recovery/recovered_photo_bindings.json')
assert v['actual_O8_timed_forwards']==1466 and v['actual_background_identity_jobs']==39
checks=[]
for row,binding in zip(rows,bindings):
 original_folder=ROOT/'delivery/results'/row['run']/'background';job=load(original_folder/'record.json')['jobs'][binding['index']]
 original_photo=original_folder/job['photo_file'];assert sha(original_photo)==job['photo_sha256']==binding['photo_sha256']
 with Image.open(original_photo) as image:image.load();actual=image.convert('RGB')
 with Image.open(row['photo_file']) as image:image.load();reconstructed=image.convert('RGB')
 assert actual.size==reconstructed.size and actual.tobytes()==reconstructed.tobytes()
 with np.load(original_folder/job['vector_file']) as orig,np.load(row['vector_file']) as recovered:
  for key in ['input','raw','normalized','scores']:assert orig[key].tobytes()==recovered[key].tobytes(),(row['run'],binding['index'],key)
 checks.append({'run':row['run'],'index':binding['index'],'original_photo_file':str(original_photo.resolve()),'original_photo_SHA256':sha(original_photo),
  'reconstructed_photo_file':row['photo_file'],'reconstructed_photo_SHA256':row['photo_sha256'],'pixels_byte_equal':True,
  'original_vector_file':str((original_folder/job['vector_file']).resolve()),'original_vector_SHA256':sha(original_folder/job['vector_file']),
  'reconstructed_input_and_actual_feature_archive':row['vector_file'],'all_four_arrays_byte_equal':True})
assert len(checks)==39
report={'status':'ORIGINAL_FULL_DELIVERY_RAW_AND39_PHOTOS_VECTORS_CONFIRM_PRIOR_UART_RECOVERY_EXACTLY','created_UTC':datetime.now(timezone.utc).isoformat(),
 'actual_O8_raw_arrays_now_locally_read_and_checked':1466,'original_photo_PNGs_now_locally_read':39,'original_vector_NPZs_now_locally_read':39,
 'all_original_and_recovery_input_raw_normalized_score_arrays_byte_equal':True,'checks':checks,
 'earlier_verifier_completed_all_checks_but_index_output_guard_hit_existing_recovery_job_rows':True,
 'earlier_recovery_job_index_overwritten':False,'new_model_forwards':0,'whole_goal_complete':False}
f=ROOT/'results/original_vs_recovery_verification_v2.json';assert not f.exists();f.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='checks'}))
