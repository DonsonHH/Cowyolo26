from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];Q=ROOT/'delivery/s256/results/qualification'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
m=load(ROOT/'evidence/s256_board_transfer.json');a=ROOT/'s256_board_results.tar.gz';assert sha(a)==m['sha256'] and a.stat().st_size==m['bytes']
out=ROOT/'s256_board_delivery';out.mkdir(exist_ok=False)
with tarfile.open(a) as t:
 assert len(t.getmembers())==m['members']
 for member in t.getmembers():
  assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
  p=(out/member.name).resolve();assert p.is_relative_to(out.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t.extractfile(member).read())
for row in load(out/'board_result_manifest.json'):assert sha(out/row['relative_file'])==row['sha256'] and (out/row['relative_file']).stat().st_size==row['bytes']
assert sha(out/'protocol.json')==sha(ROOT/'protocol/board_s256_v1.json') and sha(out/'board_s256_vectors.py')==sha(ROOT/'tools/board_s256_vectors.py')
s=load(out/'results/record.json');t=load(out/'results/terminal.json');f=load(out/'final_state.json');q=load(Q/'summary.json')
assert s['status']==t['status']=='ALL8_ACTUAL_PYNQ_COW1_CLASS_O8_VECTORS_PASS_FIXED_CPU_REFERENCE_GATES' and t['record_sha256']==sha(out/'results/record.json')
assert s['size']==q['size']==256 and s['model_checkpoint_sha256']==q['checkpoint_sha256']
assert f['proc_exists'] is False and f['PL_bit_sha256']==s['PL_after_bit_sha256']=='5da7a73bf52fd5153e25de5c28a40e2080c29e960d767008e0e804ec527bbfd8'
assert t['close_error'] is None and len(s['rows'])==8 and len(s['warmups'])==2
counts=[]
for i,row in enumerate(s['rows']):
 with np.load(Q/('parity_train_'+str(i)+'.npz')) as ar:x=ar['input'];reference=ar['reference_integer_raw'];pc=ar['native_integer_raw']
 file=out/'results'/row['raw_file'];actual=np.load(file);assert sha(file)==row['raw_file_sha256']
 assert reference.tobytes()==pc.tobytes()==actual.tobytes() and x.shape==(1,3,256,256) and actual.shape==(1,300,6)
 assert hashlib.sha256(x.tobytes()).hexdigest()==row['input_array_sha256']
 counts.append(int((actual[0,:,4]>=.2).sum()));assert row['maximum_box_error']==row['maximum_score_error']==0 and row['hardware_status']['error']=='0x0'
times=np.asarray([r['tensor_to_raw_ms'] for r in s['rows']]);result={'status':'ALL8_S256_ACTUAL_O8_RAW_BYTES_EXACT_TO_BOTH_ORIGINAL_REFERENCE_AND_PC_NATIVE',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'size':256,'checkpoint_sha256':q['checkpoint_sha256'],'class_count':1,'same_O8_bit_as192':True,
 'actual_board_qualification_vectors':8,'warmups':2,'full_raw_bytes_exact':True,'tensor_to_raw_ms':{'mean':float(times.mean()),'p95':float(np.quantile(times,.95)),'max':float(times.max())},
 'all8_training_tensor_to_raw_over200ms':bool((times>200).all()),'detections_conf02':counts,'process_terminal_and_absent':True,
 'full_video_count_accuracy_or_joint5FPS_proven':False,'whole_goal_complete':False,'archive_sha256':sha(a)}
file=ROOT/'results/s256_board_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
