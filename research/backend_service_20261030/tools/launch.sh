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
root=Path('/home/xilinx/jupyter_notebooks/cow_research_backend_service_20261030');assert not (root/'launch.json').exists() and not (root/'results').exists()
prior=Path('/home/xilinx/jupyter_notebooks/cow_research_async_highres_20261030/results/terminal.json');t=json.loads(prior.read_text());assert not (Path('/proc')/str(t['PID'])).exists()
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
a=root/'payload_v1.tar.gz';assert hashlib.sha256(a.read_bytes()).hexdigest()=='395dac506570194399b01c819a6785914f62ccbcf911c124014cb587f7852680'
allowed=['run_protocol.json','board_backend_repeats.py','background_selected_worker.py','causal_selector.py','jpeg_producer.py','test_producer.py','process_cpu.py','test_process_cpu.py']
with tarfile.open(a) as tar:
 assert len(tar.getmembers())==8
 for m in tar.getmembers():
  assert m.isfile() and m.name in allowed
  f=root/m.name;assert not f.exists();f.write_bytes(tar.extractfile(m).read())
assert hashlib.sha256((root/'run_protocol.json').read_bytes()).hexdigest()=='9559f7562949b8fadd383686ac52454a776c00859c3196a25118e46a0fe6c798'
test=subprocess.run([sys.executable,'-B',str(root/'test_producer.py')],cwd=root,capture_output=True,text=True);assert test.returncode==0,test.stderr
(root/'board_producer_behavior_tests.json').write_text(test.stdout)
test=subprocess.run([sys.executable,'-B',str(root/'test_process_cpu.py')],cwd=root,capture_output=True,text=True);assert test.returncode==0,test.stderr
(root/'board_CPU_parser_test.json').write_text(test.stdout)
with (root/'run.log').open('xb') as log:child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_backend_repeats.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'runs':4,'offered_slots_each':392,'firmware_changed':False};(root/'launch.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
