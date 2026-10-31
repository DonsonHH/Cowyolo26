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
root=Path('/home/xilinx/jupyter_notebooks/cow_research_async_highres_20261030');assert not (root/'launch.json').exists() and not (root/'results').exists()
prior=Path('/home/xilinx/jupyter_notebooks/cow_research_input_cost_v2_20261030/results/terminal.json');t=json.loads(prior.read_text());assert not (Path('/proc')/str(t['PID'])).exists()
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
a=root/'payload_v1.tar.gz';assert hashlib.sha256(a.read_bytes()).hexdigest()=='c52f032311497f58b16a16d9efba7b77a05d100140cc52e97f8ab3e603437903'
allowed=['run_protocol.json','board_async_repeats.py','background_selected_worker.py','causal_selector.py','jpeg_producer.py','test_producer.py']
with tarfile.open(a) as tar:
 assert len(tar.getmembers())==6
 for m in tar.getmembers():
  assert m.isfile() and m.name in allowed
  f=root/m.name;assert not f.exists();f.write_bytes(tar.extractfile(m).read())
assert hashlib.sha256((root/'run_protocol.json').read_bytes()).hexdigest()=='24c1d15630a981101f5b01478c82926d364d4b93de84106a3963e3d50ac8775c'
test=subprocess.run([sys.executable,'-B',str(root/'test_producer.py')],cwd=root,capture_output=True,text=True);assert test.returncode==0,test.stderr
(root/'board_producer_behavior_tests.json').write_text(test.stdout)
with (root/'run.log').open('xb') as log:child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_async_repeats.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'runs':4,'offered_slots_each':392,'firmware_changed':False};(root/'launch.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
