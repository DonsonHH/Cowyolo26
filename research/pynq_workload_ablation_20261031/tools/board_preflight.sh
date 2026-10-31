set -euo pipefail
test "$(id -un)" = root
XILINX_XRT=/usr /usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,fcntl,subprocess
from pynq import PL
root=Path('/home/xilinx/jupyter_notebooks')
names=[
 root/'yolo26_optimization_8/device_initialize.py',
 root/'yolo26_optimization_8/native_graph.py',
 root/'yolo26_optimization_8/hardware/accepted/optimization_8_resident.bit',
 root/'yolo26_optimization_8/hardware/accepted/optimization_8_resident.hwh']
records=[]
for p in names:
 row={'file':str(p),'exists':p.is_file()}
 if p.is_file():
  row.update({'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
  if p.suffix=='.py':row['source']=p.read_text()
 records.append(row)
lock=root/'yolo26_stage_d/reports/accelerator_job.lock'
with lock.open('rb')as stream:
 fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
own=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  args=(proc/'cmdline').read_bytes().split(bytes([0]))
  scripts=[part.decode('utf-8','replace')for part in args if b'/cow_research_'in part and part.endswith(b'.py')]
  if scripts:own.append({'PID':int(proc.name),'scripts':scripts})
 except (OSError,PermissionError):pass
print(json.dumps({'status':'READONLY_NEW_WORKLOAD_ABLATION_PREFLIGHT_NO_MODEL_FORWARD','created_board_UTC':datetime.now(timezone.utc).isoformat(),
 'uid':os.getuid(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'uptime':Path('/proc/uptime').read_text().strip(),'PL_bitfile_name':PL.bitfile_name,'PL_IP_names':list(PL.ip_dict),
 'accelerator_lock_available':True,'own_task_script_processes':own,'memory':Path('/proc/meminfo').read_text(),
 'affinity':sorted(os.sched_getaffinity(0)),'records':records,'PL_programmed_by_preflight':False,'new_model_forwards':0}),flush=True)
PY
