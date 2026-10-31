set -euo pipefail
test "$(id -un)" = xilinx
id -un
hostname
uname -r
ip -4 -o addr show dev eth0
cat /proc/sys/kernel/random/boot_id
cat /proc/uptime
systemctl is-active ssh jupyter || true
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import hashlib,json
root=Path('/home/xilinx/jupyter_notebooks/cow_research_identity_trigger_pair_20261030')
def get(path):
 if not path.is_file():return {'exists':False}
 raw=path.read_bytes();v={'exists':True,'sha256':hashlib.sha256(raw).hexdigest()}
 try:v['data']=json.loads(raw)
 except Exception as error:v['parse_error']=repr(error)
 return v
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
record=get(root/'results/record.json');state=record.get('data',{})
value={'status':'ORIGINAL_TRIGGER_TASK_RECOVERY_READONLY_NO_MODEL_OR_PL_IMPORT',
 'collection_boot_id':boot,'source_boot_id':state.get('boot_id'),
 'task_directory_exists':root.is_dir(),
 'protocol_sha256':hashlib.sha256((root/'run_protocol.json').read_bytes()).hexdigest()if(root/'run_protocol.json').is_file()else None,
 'parent_PID10099_proc_exists_now':Path('/proc/10099').exists(),
 'record_status':state.get('status'),'terminal':get(root/'results/terminal.json'),'progress':get(root/'results/progress.json'),
 'cases':[{k:c[k]for k in['run','identity_model','processed_frames','skipped_slots','deadline_misses','source_down_count','actual_background_jobs','processed_per_second_over_offered_duration']}for c in state.get('cases',[])],
 'saved_result_file_count':sum(p.is_file()for p in(root/'results').rglob('*'))if(root/'results').exists()else 0,
 'previous_recovery_transfer':get(root/'interruption_recovery_transfer_v1.json'),
 'reprogrammed_or_loaded_PL':False,'new_model_forwards':0,'original_experiment_restarted':False}
print(json.dumps(value),flush=True)
PY
