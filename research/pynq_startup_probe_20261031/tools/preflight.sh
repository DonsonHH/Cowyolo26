set -euo pipefail
test "$(id -un)" = root
XILINX_XRT=/usr /usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,fcntl,subprocess
from pynq import PL
base=Path('/home/xilinx/jupyter_notebooks')
prior=base/'cow_research_workload_ablation_20261031'
plan=json.loads((prior/'run_protocol.json').read_text())
end=json.loads((prior/'results/terminal.json').read_text())
assert end['status']=='FAILED' and not(Path('/proc')/str(end['PID'])).exists()
assert PL.bitfile_name and hashlib.sha256(Path(PL.bitfile_name).read_bytes()).hexdigest()==plan['O8_bit_sha256']
with(base/'yolo26_stage_d/reports/accelerator_job.lock').open('rb')as stream:
 fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(stream,fcntl.LOCK_UN)
warm=base/'cow_research_ncnn_identity_20261029/vectors/old_gallery_000.npz'
files=[prior/'board_workload_ablation.py',prior/'background_fixed_worker.py',
       base/'cow_research_mosaic192_video_20261030/board_input_manifest.json',warm]
processes=[]
for path in Path('/proc').iterdir():
 if not path.name.isdigit():continue
 try:
  args=(path/'cmdline').read_bytes().split(bytes([0]))
  if any(arg.startswith(b'/home/xilinx/jupyter_notebooks/cow_research_')and arg.endswith(b'.py')for arg in args):
   processes.append({'PID':int(path.name),'args':[arg.decode(errors='replace')for arg in args]})
 except(OSError,PermissionError):pass
print(json.dumps({'status':'READONLY_STARTUP_DIAGNOSTIC_PREFLIGHT_NO_FORWARD_OR_PL_PROGRAMMING',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'PL_bitfile_name':PL.bitfile_name,'PL_SHA256':hashlib.sha256(Path(PL.bitfile_name).read_bytes()).hexdigest(),
 'shared_lock_available':True,'task_processes':processes,'page_size_bytes':os.sysconf('SC_PAGE_SIZE'),
 'smaps_rollup':Path('/proc/self/smaps_rollup').read_text(),'meminfo':Path('/proc/meminfo').read_text(),
 'services':{name:subprocess.run(['systemctl','is-active',name],capture_output=True,text=True).stdout.strip()for name in['ssh','jupyter']},
 'files':[{'file':str(path),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}for path in files],
 'new_model_forwards':0}),flush=True)
PY
