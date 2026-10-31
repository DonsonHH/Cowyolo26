set -euo pipefail
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,tarfile,hashlib,subprocess,sys,os,fcntl
root=Path('/home/xilinx/jupyter_notebooks/cow_research_input_cost_20261030');assert not (root/'launch.json').exists() and not (root/'results').exists()
prior=Path('/home/xilinx/jupyter_notebooks/cow_research_causal_photo_20261030/results/terminal.json');t=json.loads(prior.read_text());assert not (Path('/proc')/str(t['PID'])).exists()
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
a=root/'payload_v1.tar.gz';assert hashlib.sha256(a.read_bytes()).hexdigest()=='5c367c4f6da14198724a5ce4447a02a7681eb84ce29a036a46b0ab54d3b1ff3d'
with tarfile.open(a) as tar:
 assert len(tar.getmembers())==2
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['protocol.json','board_benchmark.py']
  f=root/m.name;assert not f.exists();f.write_bytes(tar.extractfile(m).read())
assert hashlib.sha256((root/'protocol.json').read_bytes()).hexdigest()=='26945e0392065e951b92703c5adc5aa55420a0f3822c2e2612d5b36189b975c0'
with (root/'run.log').open('xb') as log:child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_benchmark.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'measured_O8_forwards':128,'input_images':16,'new_firmware_programming':False};(root/'launch.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
