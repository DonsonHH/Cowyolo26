from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,fcntl,tarfile
from pynq import PL
ROOT=Path('/home/xilinx/jupyter_notebooks/cow_research_workload_ablation_20261031')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
assert ROOT.is_dir()and sha(ROOT/'run_protocol.json')=='9329f1fc27a2059ffbddd459b289b69061d9f05f4f51e1e1ca840e5528456cb8'
plan=load(ROOT/'run_protocol.json');state=load(ROOT/'results/record.json');terminal=load(ROOT/'results/terminal.json')
launch=load(ROOT/'launch.json');boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot==launch['boot_id']==state['boot_id']==plan['expected_boot_id']
assert state['status']==terminal['status']=='ALL8_WORKLOAD_2X2_MIRROR_ORDER_REPEATS_COMPLETE'
assert terminal['record_sha256']==sha(ROOT/'results/record.json')and terminal['close_error']is None
assert not(Path('/proc')/str(launch['PID'])).exists()
assert len(state['cases'])==8
children=[]
for spec in plan['runs']:
 record=load(ROOT/'results'/spec['run']/'background/record.json')
 end=load(ROOT/'results'/spec['run']/'background/terminal.json')
 assert end['record_sha256']==sha(ROOT/'results'/spec['run']/'background/record.json')
 assert record['status']==end['status']=='ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE'
 assert not(Path('/proc')/str(end['PID'])).exists()
 children.append({'run':spec['run'],'PID':end['PID'],'proc_exists':False,'jobs':record['model_forwards']})
runtime=[{'file':row['file'],'expected_sha256':row['sha256'],'actual_sha256':sha(Path(row['file']))}for row in plan['runtime_files']]
assert all(row['expected_sha256']==row['actual_sha256']for row in runtime)
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock')
with lock.open('rb')as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
assert PL.bitfile_name and sha(Path(PL.bitfile_name))==plan['O8_bit_sha256']==state['PL_after_sha256']
def save(path,value):
 assert not path.exists();path.write_bytes((json.dumps(value,indent=2)+'\n').encode())
final={'status':'ALL8_TASK_AND_CHILDREN_TERMINAL_RUNTIME_HASHES_AND_CURRENT_O8_LOCK_VERIFIED',
       'created_board_UTC':datetime.now(timezone.utc).isoformat(),'boot_id':boot,'parent_PID':launch['PID'],'parent_absent':True,
       'children':children,'runtime_files':runtime,'all_runtime_hashes_match':True,'shared_lock_available':True,
       'PL_bitfile_name':PL.bitfile_name,'PL_SHA256':sha(Path(PL.bitfile_name)),
       'collection_programmed_PL_or_ran_models':False,'collector_PID':os.getpid(),'new_model_forwards':0}
save(ROOT/'final_state.json',final)
paths=sorted([p for p in(ROOT/'results').rglob('*')if p.is_file()]+[ROOT/'run_protocol.json',ROOT/'launch.json',ROOT/'run.log',ROOT/'final_state.json']+
             [ROOT/row['file']for row in plan['payload_files']]+[Path(__file__)])
assert len({str(p)for p in paths})==len(paths)
manifest=ROOT/'result_manifest.json'
rows=[{'file':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)}for p in paths];save(manifest,rows)
archive=ROOT/'workload_delivery_v1.tar.xz';assert not archive.exists()
with tarfile.open(archive,'w:xz',preset=3)as tar:
 for path in paths+[manifest]:tar.add(path,arcname=path.relative_to(ROOT).as_posix(),recursive=False)
for row in rows:assert sha(ROOT/row['file'])==row['sha256']
os.sync()
transfer={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(paths)+1,'manifest_files':len(paths),'new_model_forwards':0}
save(ROOT/'transfer.json',transfer);print(json.dumps(transfer),flush=True)
