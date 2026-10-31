from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,ast,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
 assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
red=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools/check_target.py')],capture_output=True,text=True);assert red.returncode==1
save(ROOT/'results/original_periodic_target_red.json',{'exit_code':red.returncode,'result':json.loads(red.stdout)})
old=load(PROJECT/'causal_photo_20261030/protocol/run_v1.json');manifest=load(PROJECT/'pynq_periodic_joint_20261030/camera_delivery/manifest.json')
inputs=load(PROJECT/'pynq_mosaic192_eval_20261030/board_delivery/board_input_manifest.json');inputs={r['frame0']:r for r in inputs if r['scene']=='original'}
rows=[]
for index in range(0,391,26):
 r=manifest[index];q=inputs[r['frame0']];rows.append({'slot':index,'frame0':r['frame0'],'camera_file':r['file'],'camera_bytes':r['bytes'],'camera_sha256':r['sha256'],'input_file':q['file'],'input_sha256':q['sha256']})
assert len(rows)==16 and rows[-1]['slot']==390
runner=ROOT/'tools/board_benchmark.py';ast.parse(runner.read_text(encoding='utf-8'))
p={'status':'FROZEN_BEFORE_READ_COST_MICROBENCHMARK','created_UTC':datetime.now(timezone.utc).isoformat(),'runner_sha256':sha(runner),'plan_sha256':sha(ROOT/'计划与验收.md'),
 'source_rows':rows,'runtime_files':old['runtime_files'],'O8_bit_sha256':old['O8_bit_sha256'],'foreground_source_model':old['foreground_source_model'],
 'camera_root':old['camera_root'],'modes':['read_only','after_actual_O8'],'methods':['bytes','readinto'],'cache_requests':['cold_requested','prewarmed'],
 'repeats':2,'actual_O8_measured_forwards':128,'actual_O8_qualification_forwards':8,'actual_O8_warmups':2,'expected_rows':256,
 'representative_frames_are_not_independent_sessions':True,'inference_then_read_mirrors_prior_order':True,
 'graph_mode_has_no_tracker_identity_or_periodic_release':True,'only16_ready192_inputs_in_memory_not_prior392':True,
 'no_global_drop_caches_or_swap_control':True,'cold_request_not_storage_proof':True,'process_read_bytes_and_CPU_and_faults_recorded':True,
 'extra_copy_and_pickle_scope':'Additional_after_timer_microbench_only;not_measured_interprocess_delivery_or_full_request_serialization',
 'new_training_updates':0,'real_camera_or_RFID':False,'policy_adoption_in_this_microbench':False,'whole_goal_complete':False}
save(ROOT/'protocol/run_v1.json',p)
a=ROOT/'payload_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
 tar.add(ROOT/'protocol/run_v1.json',arcname='protocol.json');tar.add(runner,arcname='board_benchmark.py')
meta={'bytes':a.stat().st_size,'sha256':sha(a),'protocol_sha256':sha(ROOT/'protocol/run_v1.json'),'members':2};save(ROOT/'results/payload_manifest.json',meta)
remote='/home/xilinx/jupyter_notebooks/cow_research_input_cost_20261030'
script='''set -euo pipefail
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,tarfile,hashlib,subprocess,sys,os,fcntl
root=Path('REMOTE');assert not (root/'launch.json').exists() and not (root/'results').exists()
prior=Path('/home/xilinx/jupyter_notebooks/cow_research_causal_photo_20261030/results/terminal.json');t=json.loads(prior.read_text());assert not (Path('/proc')/str(t['PID'])).exists()
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
a=root/'payload_v1.tar.gz';assert hashlib.sha256(a.read_bytes()).hexdigest()=='ARCHIVE_SHA'
with tarfile.open(a) as tar:
 assert len(tar.getmembers())==2
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['protocol.json','board_benchmark.py']
  f=root/m.name;assert not f.exists();f.write_bytes(tar.extractfile(m).read())
assert hashlib.sha256((root/'protocol.json').read_bytes()).hexdigest()=='PROTOCOL_SHA'
with (root/'run.log').open('xb') as log:child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_benchmark.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'measured_O8_forwards':128,'input_images':16,'new_firmware_programming':False};(root/'launch.json').write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r))
PY
'''.replace('REMOTE',remote).replace('ARCHIVE_SHA',meta['sha256']).replace('PROTOCOL_SHA',meta['protocol_sha256'])
(ROOT/'tools/launch.sh').write_text(script,encoding='utf-8')
print(json.dumps({'status':p['status'],'frames':len(rows),**meta}))
