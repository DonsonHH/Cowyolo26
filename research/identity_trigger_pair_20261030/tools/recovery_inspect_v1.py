"""Small read-only probe for the original task after access returns."""
from pathlib import Path
import hashlib,json
ROOT=Path('/home/xilinx/jupyter_notebooks/cow_research_identity_trigger_pair_20261030')
def get(p):
 if not p.is_file():return {'exists':False}
 try:return {'exists':True,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'data':json.loads(p.read_text())}
 except Exception as error:return {'exists':True,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'parse_error':repr(error)}
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();state=get(ROOT/'results/record.json');record=state.get('data',{})
v={'status':'ORIGINAL_TRIGGER_TASK_READONLY_RECOVERY_INSPECTION','boot_id':boot,'source_boot_id':record.get('boot_id'),'task_directory_exists':ROOT.is_dir(),
 'protocol_sha256':hashlib.sha256((ROOT/'run_protocol.json').read_bytes()).hexdigest()if(ROOT/'run_protocol.json').exists()else None,
 'parent_PID_10099_proc_exists_now':(Path('/proc')/'10099').exists(),'record_status':record.get('status'),
 'terminal':get(ROOT/'results/terminal.json'),'progress':get(ROOT/'results/progress.json'),
 'cases':[{k:row[k]for k in['run','identity_model','processed_frames','skipped_slots','deadline_misses','source_down_count','actual_background_jobs','processed_per_second_over_offered_duration']}for row in record.get('cases',[])],
 'source_readable_files':len([p for p in(ROOT/'results').rglob('*')if p.is_file()])if(ROOT/'results').exists()else 0,
 'O8_loaded_or_modified':False,'new_model_forwards':0}
print(json.dumps(v),flush=True)
