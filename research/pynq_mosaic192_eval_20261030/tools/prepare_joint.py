from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,ast,tarfile
PROJECT=Path(__file__).resolve().parents[2];ROOT=PROJECT/'pynq_mosaic192_joint_20261030';OLD=PROJECT/'pynq_capture_encoding_20261030'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
for name in ['tools','protocol','results','evidence']:(ROOT/name).mkdir(parents=True,exist_ok=True)
worker=ROOT/'tools/background_capture0_worker.py';assert not worker.exists();worker.write_bytes((OLD/'tools/background_capture0_worker.py').read_bytes())
runner=(OLD/'tools/board_periodic_capture0.py').read_text(encoding='utf-8')
runner=runner.replace('cow_research_rot192_video_20261029','cow_research_mosaic192_video_20261030').replace('cow_research_o8_rot192_qual_20261029','cow_research_o8_mosaic192_qual_20261030')
runner=runner.replace("VIDEO/'results_v2/","VIDEO/'results/")
needle="  for case in p['cases']:\n   folder=out/case;"
replace="  for run_spec in p['runs']:\n   case=run_spec['policy'];run_name=run_spec['run'];folder=out/run_name;"
assert runner.count(needle)==1;runner=runner.replace(needle,replace)
runner=runner.replace("'case':case,'offered_slots':392","'case':case,'run':run_name,'repeat':run_spec['repeat'],'offered_slots':392")
runner=runner.replace("'case':case,'processed_slots_this_case'","'case':case,'run':run_name,'processed_slots_this_case'")
runner=runner.replace("assert len(state['cases'])==3","assert len(state['cases'])==6")
runner=runner.replace('ALL_THREE392_SLOT_LOSSLESS_CAPTURE_ENCODING_CONTROLS_COMPLETE','ALL_SIX392_SLOT_MOSAIC192_SAME_BOARD_REPEATS_COMPLETE')
needle="  assert sha(PL.bitfile_name)==p['O8_bit_sha256']"
replace="""  vt=load(VIDEO/'results/terminal.json');vr=load(VIDEO/'results/record.json')
  assert vt['status']==vr['status']=='ALL2654_ACTUAL_O8_VIDEO_INPUTS_AND_REAL_ARM_COUNTER_PATHS_COMPLETE'
  assert vt['record_sha256']==sha(VIDEO/'results/record.json') and not (Path('/proc')/str(vt['PID'])).exists()
  assert vr['model_checkpoint_sha256']==p['foreground_source_model'] and vr['actual_anchor_integer_parity_bytes_exact']==8
  assert sha(PL.bitfile_name)==p['O8_bit_sha256']"""
assert runner.count(needle)==1;runner=runner.replace(needle,replace)
file=ROOT/'tools/board_joint_repeats.py';assert not file.exists();file.write_text(runner,encoding='utf-8',newline='\n');ast.parse(runner)
p=load(OLD/'protocol/periodic_v1.json')
for name in ['previous_actual_no_skip_model_count','previous_template_sha256','periodic_inputs_model_threshold_sampling_policy_unchanged',
    'previous_periodic_execution_started','previous_both_cases_review_sha256','all_other_input_model_threshold_gallery_photo_stage_and_periodic_rules_unchanged',
    'model_and_calibration_changes','three_cases_single_run_each_not_statistical_significance','backend_runtime_photo_pixel_and_input_parity_against_prior_required']:
    p.pop(name,None)
cases=['foreground_only','foreground_with_identity','foreground_idle_identity']
runs=[]
for repeat,order in [(1,cases),(2,list(reversed(cases)))]:
    for policy in order:runs.append({'run':'r'+str(repeat)+'_'+policy,'repeat':repeat,'policy':policy})
qualification=PROJECT/'pynq_mosaic192_compile_20261030';candidate=load(PROJECT/'mosaic_pair_20261030/results/retained_candidate.json')
q=load(qualification/'delivery/results/qualification/summary.json')
p.update({'status':'FROZEN_BEFORE_TWO_REPEATS_SIX_392_SLOT_SAME_BOARD_RUNS','created_UTC':datetime.now(timezone.utc).isoformat(),
    'runs':runs,'cases':cases,'repeats':2,'same_public_replay_repeats_not_independent_farm_sessions':True,
    'foreground_source_model':candidate['checkpoint_sha256'],'model_name':candidate['name'],
    'graph_sha256':q['graph_sha256'],'resident_plan_sha256':q['resident_plan_sha256'],
    'actual_same_model_full_video_terminal_required_before_worker_start':True,'actual_video_state_bound_at_execution':True,
    'fixed_intervention':'New_fixed_mosaic050_model;two_counterbalanced_order_repeats_of_existing_three_execution_policies;PNG0',
    'older_model_single_run_not_same_workload_causal_baseline':True,'mosaic_model_and_calibration_changed_relative_to_prior_joint_phase':True,
    'current_identity_gallery_and_threshold_unchanged':True,'count_triggered_jobs_per_run_not_fixed_assumed11':True,
    'retrospective_gallery_registered_after_Aug14_source_event':True,
    'payload_files':[{'file':f.name,'sha256':sha(f),'bytes':f.stat().st_size} for f in [worker,file]],
    'new_training_updates':0,'new_independent_test':False,'whole_goal_complete':False})
model_root='/home/xilinx/jupyter_notebooks/cow_research_o8_mosaic192_qual_20261030'
p['runtime_files'].extend([{'file':model_root+'/program/graph.bin','sha256':q['graph_sha256']},{'file':model_root+'/resident_plan/resident_plan.bin','sha256':q['resident_plan_sha256']}])
protocol=ROOT/'protocol/run_v1.json';assert not protocol.exists();protocol.write_text(json.dumps(p,indent=2)+'\n',encoding='utf-8')
a=ROOT/'joint_payload_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
    for f,name in [(worker,worker.name),(file,file.name),(protocol,'run_protocol.json')]:tar.add(f,arcname=name,recursive=False)
meta={'archive_bytes':a.stat().st_size,'archive_sha256':sha(a),'protocol_sha256':sha(protocol),'members':3,
    'board_task_root':'/home/xilinx/jupyter_notebooks/cow_research_mosaic192_joint_20261030'}
f=ROOT/'evidence/payload.json';assert not f.exists();f.write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
create='''set -euo pipefail
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json
root=Path('{TASK_ROOT}');root.mkdir(exist_ok=False);print(json.dumps({'status':'NEW_JOINT_REPEATS_DIRECTORY_CREATED','path':str(root),'new_model_or_PL_actions':0}))
PY
'''.replace('{TASK_ROOT}',meta['board_task_root'])
(ROOT/'tools/create_task.sh').write_text(create,encoding='utf-8',newline='\n')
launch='''set -euo pipefail
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,os,sys,subprocess,fcntl
root=Path('{TASK_ROOT}');video=Path('/home/xilinx/jupyter_notebooks/cow_research_mosaic192_video_20261030')
terminal=json.loads((video/'results/terminal.json').read_text());assert terminal['status']=='ALL2654_ACTUAL_O8_VIDEO_INPUTS_AND_REAL_ARM_COUNTER_PATHS_COMPLETE'
assert not (Path('/proc')/str(terminal['PID'])).exists()
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
assert not (root/'launch.json').exists() and not (root/'results').exists()
a=root/'payload.tar.gz';assert hashlib.sha256(a.read_bytes()).hexdigest()=='{PAYLOAD_HASH}'
with tarfile.open(a) as tar:
 assert len(tar.getmembers())==3
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['run_protocol.json','background_capture0_worker.py','board_joint_repeats.py']
  f=root/m.name;assert not f.exists();f.write_bytes(tar.extractfile(m).read())
assert hashlib.sha256((root/'run_protocol.json').read_bytes()).hexdigest()=='{PROTOCOL_HASH}'
with (root/'run.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_joint_repeats.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'runs':6,'offered_slots_each':392,'same_model_full_video_PID_terminal':terminal['PID'],'new_firmware_programming':False}
(root/'launch.json').write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r))
PY
'''.replace('{TASK_ROOT}',meta['board_task_root']).replace('{PAYLOAD_HASH}',meta['archive_sha256']).replace('{PROTOCOL_HASH}',meta['protocol_sha256'])
(ROOT/'tools/launch.sh').write_text(launch,encoding='utf-8',newline='\n')
status='''set -euo pipefail
test "$(id -un)" = xilinx
python3 - <<'PY'
from pathlib import Path
import json,subprocess
root=Path('{TASK_ROOT}');launch=json.loads((root/'launch.json').read_text())
r={'launch':launch,'ps':subprocess.run(['ps','-p',str(launch['PID']),'-o','pid,state,etimes,rss,comm'],capture_output=True,text=True).stdout,
 'progress':(root/'results/progress.json').read_text() if (root/'results/progress.json').exists() else None,
 'terminal':(root/'results/terminal.json').read_text() if (root/'results/terminal.json').exists() else None,
 'completed_cases':json.loads((root/'results/record.json').read_text()).get('cases',[]) if (root/'results/record.json').exists() else [],
 'log_tail':(root/'run.log').read_text(errors='replace')[-2000:]}
print(json.dumps(r))
PY
'''.replace('{TASK_ROOT}',meta['board_task_root'])
(ROOT/'tools/status.sh').write_text(status,encoding='utf-8',newline='\n')
print(json.dumps(meta))
