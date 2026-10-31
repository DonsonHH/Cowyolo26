set -euo pipefail
test "$(id -un)" = root
test -d /home/xilinx/jupyter_notebooks
export XILINX_XRT=/usr
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,socket,fcntl
from pynq import PL
bit=PL.bitfile_name
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock')
available=None
if lock.exists():
 with lock.open('r') as f:
  try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);available=True;fcntl.flock(f,fcntl.LOCK_UN)
  except BlockingIOError:available=False
processes=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  argv=(proc/'cmdline').read_bytes().split(b'\0');text=' '.join(v.decode('utf-8','replace') for v in argv)
  if any(word in text for word in ['cow_research_','native_queue','yolo26_optimization_8']):
   script=next((v.decode('utf-8','replace') for v in argv if v.endswith(b'.py')),'')
   if script:processes.append({'PID':int(proc.name),'script_basename':Path(script).name,'cwd':str((proc/'cwd').resolve())})
 except (FileNotFoundError,PermissionError,ProcessLookupError):pass
ports={}
for port in [22,9090]:
 try:
  s=socket.create_connection(('127.0.0.1',port),timeout=1);s.close();ports[str(port)]=True
 except OSError:ports[str(port)]=False
r={'status':'READ_ONLY_BOARD_PRECHECK','board_clock_UTC':datetime.now(timezone.utc).isoformat(),
 'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'PL_bitfile':bit,
 'PL_bitfile_sha256':hashlib.sha256(Path(bit).read_bytes()).hexdigest() if bit and Path(bit).is_file() else None,
 'shared_accelerator_lock_exists':lock.exists(),'shared_accelerator_lock_available':available,
 'matching_task_processes':processes,'listening_ports':ports,'video_devices':[str(v) for v in Path('/dev').glob('video*')],
 'memory_available_lines':[s for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith(('MemTotal:','MemAvailable:','CmaFree:'))],
 'new_network_forwards':0,'new_PL_programming_actions':0,'environment_changed':False}
print(json.dumps(r))
PY
