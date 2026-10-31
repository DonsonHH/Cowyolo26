set -euo pipefail
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,os,sys,subprocess,fcntl
root=Path('/home/xilinx/jupyter_notebooks/cow_research_causal_photo_20261030');old=Path('/home/xilinx/jupyter_notebooks/cow_research_mosaic192_joint_20261030')
t=json.loads((old/'results/terminal.json').read_text());assert t['status']=='ALL_SIX392_SLOT_MOSAIC192_SAME_BOARD_REPEATS_COMPLETE' and not (Path('/proc')/str(t['PID'])).exists()
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
assert not (root/'launch.json').exists() and not (root/'results').exists()
a=root/'payload_v1.tar.gz';assert hashlib.sha256(a.read_bytes()).hexdigest()=='9ac29740c1c6afb3291fd8cc92ecda2a63a1c1fde50f6605ef3bc511dea35f39'
with tarfile.open(a) as tar:
 assert len(tar.getmembers())==4
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['run_protocol.json','board_causal_repeats.py','background_selected_worker.py','causal_selector.py']
  f=root/m.name;assert not f.exists();f.write_bytes(tar.extractfile(m).read())
assert hashlib.sha256((root/'run_protocol.json').read_bytes()).hexdigest()=='396286dc4257422dbed79ea8d94942e89e767213aeb1af00287ee08837ea4dae'
with (root/'run.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_causal_repeats.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'runs':6,'offered_slots_each':392,'new_firmware_programming':False,'new_model_or_threshold_tuning':False}
(root/'launch.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
