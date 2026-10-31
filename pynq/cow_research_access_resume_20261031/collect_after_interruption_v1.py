"""Collect saved originals after an interruption; never launch a model or load PL."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,tarfile

ROOT=Path('/home/xilinx/jupyter_notebooks/cow_research_identity_trigger_pair_20261030')
EXPECTED_PROTOCOL='4217824d2964e56218c566a73096a2f282c94020f3176c74bf86cef9a270513c'
EXPECTED_SOURCE_BOOT='9ecd4ca1-edd1-45f8-aa09-dfac2a089f2f'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def parse(p):
 if not p.is_file():return {'exists':False}
 try:return {'exists':True,'sha256':sha(p),'data':json.loads(p.read_text())}
 except Exception as error:return {'exists':True,'sha256':sha(p),'parse_error':repr(error)}
def save(p,v):assert not p.exists();p.write_bytes(json.dumps(v,indent=2).encode()+bytes([10]))

assert ROOT.is_dir()and ROOT.parent==Path('/home/xilinx/jupyter_notebooks')
assert sha(ROOT/'run_protocol.json')==EXPECTED_PROTOCOL
plan=json.loads((ROOT/'run_protocol.json').read_text());boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
state=parse(ROOT/'results/record.json');terminal=parse(ROOT/'results/terminal.json');record=state.get('data',{})
if 'boot_id'in record:assert record['boot_id']==EXPECTED_SOURCE_BOOT
running=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  argv=(proc/'cmdline').read_bytes().replace(bytes([0]),b' ')
  if str(ROOT/'board_trigger_repeats.py').encode()in argv:running.append({'PID':int(proc.name),'cmdline':argv.decode('utf-8','replace')})
 except(OSError,PermissionError):pass
assert not running,'Original task is currently live: observe that task; do not archive a changing source'
own_pids=[]
for spec in plan['runs']:
 bg=parse(ROOT/'results'/spec['run']/'background/terminal.json')
 if 'data'in bg:own_pids.append(bg['data']['PID'])
if boot==EXPECTED_SOURCE_BOOT:
 # A same-boot orphan still computing must be observed, not silently interrupted.
 assert all(not(Path('/proc')/str(pid)).exists()for pid in own_pids)
 original_PID=terminal.get('data',{}).get('PID',record.get('PID',10099));assert not(Path('/proc')/str(original_PID)).exists()

inventory=[];paths=[]
for p in sorted((ROOT/'results').rglob('*'))if(ROOT/'results').exists()else[]:
 if p.is_symlink():raise RuntimeError('Unexpected source result symlink: '+str(p))
 if p.is_file():paths.append(p)
for name in['run_protocol.json','launch.json','run.log','board_trigger_repeats.py','background_selected_worker.py','causal_selector.py','jpeg_producer.py','process_cpu.py','collect_results.py']:
 p=ROOT/name
 if p.is_file():paths.append(p)
for p in paths:inventory.append({'file':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)})
runtime=[]
for row in plan['runtime_files']:
 p=Path(row['file']);runtime.append({'file':row['file'],'expected_sha256':row['sha256'],'exists':p.is_file(),'actual_sha256':sha(p)if p.is_file()else None})
cases=[]
for spec in plan['runs']:
 folder=ROOT/'results'/spec['run'];done=parse(folder/'background/terminal.json');jobs=parse(folder/'background/record.json')
 cases.append({'run':spec['run'],'identity_model':spec['identity_model'],'background_terminal':done,'background_status':jobs.get('data',{}).get('status'),'saved_background_jobs':len(jobs.get('data',{}).get('jobs',[])),
               'raw_exists':(folder/'actual_raw.npz').is_file(),'trace_exists':(folder/'counter_trace.json.gz').is_file(),'timing_exists':(folder/'timing_rows.json').is_file()})
source_terminal=terminal.get('data',{});complete=record.get('status')==source_terminal.get('status')=='ALL4_ACTUAL_COUNT_TRIGGER_OLD_NEW_NEW_OLD_ASYNC_CAUSAL_IDENTITY_RUNS_COMPLETE'
if complete:assert source_terminal['record_sha256']==sha(ROOT/'results/record.json')
value={'status':'SAVED_ORIGINALS_COLLECTED_AFTER_ACCESS_INTERRUPTION_COMPLETION_REQUIRES_INDEPENDENT_VERIFICATION','created_host_untrusted_board_UTC':datetime.now(timezone.utc).isoformat(),
 'collector_PID':os.getpid(),'source_boot_id':EXPECTED_SOURCE_BOOT,'collection_boot_id':boot,'boot_changed_since_experiment':boot!=EXPECTED_SOURCE_BOOT,
 'source_parent_terminal':terminal,'source_parent_record_status':record.get('status'),'source_parent_terminal_consistent_complete':complete,'case_inventory':cases,'runtime_checks':runtime,
 'all_bound_runtime_files_match_now':all(r['actual_sha256']==r['expected_sha256']for r in runtime),'current_loaded_PL_observed':False,
 'no_current_loaded_O8_invariant_inferred_after_reboot':True,'models_or_PL_loaded_or_programmed':False,'new_model_forwards':0,'new_training_updates':0,'whole_goal_complete':False}
reason=ROOT/'interruption_recovery_v1.json';save(reason,value);paths.append(reason)
manifest=ROOT/'interruption_recovery_manifest_v1.json';save(manifest,[{'file':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}for p in paths]);paths.append(manifest)
a=ROOT/'trigger_pair_interruption_originals_v1.tar.xz';assert not a.exists()
with tarfile.open(a,'w:xz',preset=3)as tar:
 for p in sorted(paths,key=lambda x:(x.suffix,x.name,str(x))):tar.add(p,arcname=p.relative_to(ROOT).as_posix(),recursive=False)
# Re-read every source file so a changing or damaged source cannot be called stable.
for row in inventory:assert sha(ROOT/row['file'])==row['sha256']
os.sync();v={'archive':str(a),'bytes':a.stat().st_size,'sha256':sha(a),'members':len(paths),'manifest_files':len(paths)-1,'source_terminal_consistent_complete':complete,'new_model_forwards':0}
save(ROOT/'interruption_recovery_transfer_v1.json',v);print(json.dumps(v),flush=True)
