set -euo pipefail
test "$(id -un)" = xilinx
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import fcntl,hashlib,json,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_identity_trigger_pair_20261030')
plan=json.loads((root/'run_protocol.json').read_text())
checks=[]
for row in plan['runtime_files']:
 path=Path(row['file']);actual=hashlib.sha256(path.read_bytes()).hexdigest()
 checks.append({'file':row['file'],'sha256':actual,'matches':actual==row['sha256']})
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock')
free=False
with lock.open('rb')as handle:
 try:fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB);free=True;fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
 except BlockingIOError:pass
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
print(json.dumps({'status':'POST_COLLECTION_READONLY_RUNTIME_SERVICES_LOCK_AND_BOOT_CHECK',
 'boot_id':boot,'uptime':Path('/proc/uptime').read_text().strip(),
 'collector_PID979_exists':Path('/proc/979').exists(),'accelerator_lock_free':free,
 'runtime_files_checked':len(checks),'all_bound_runtime_files_match':all(r['matches']for r in checks),
 'services':{name:subprocess.run(['systemctl','is-active',name],capture_output=True,text=True).stdout.strip()for name in['ssh','jupyter']},
 'eth0_carrier':Path('/sys/class/net/eth0/carrier').read_text().strip(),
 'IPv4':subprocess.run(['ip','-4','-o','addr','show','dev','eth0'],capture_output=True,text=True).stdout.strip(),
 'FPGA_manager_state':Path('/sys/class/fpga_manager/fpga0/state').read_text().strip(),
 'current_loaded_O8_identity_not_claimed':True,'runtime_files':checks,
 'new_model_forwards':0,'PL_or_encoder_loaded_by_recovery':False,'original_experiment_restarted':False}),flush=True)
PY
