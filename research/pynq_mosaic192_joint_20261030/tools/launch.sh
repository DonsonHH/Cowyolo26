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
root=Path('/home/xilinx/jupyter_notebooks/cow_research_mosaic192_joint_20261030');video=Path('/home/xilinx/jupyter_notebooks/cow_research_mosaic192_video_20261030')
terminal=json.loads((video/'results/terminal.json').read_text());assert terminal['status']=='ALL2654_ACTUAL_O8_VIDEO_INPUTS_AND_REAL_ARM_COUNTER_PATHS_COMPLETE'
assert not (Path('/proc')/str(terminal['PID'])).exists()
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
assert not (root/'launch.json').exists() and not (root/'results').exists()
a=root/'payload.tar.gz';assert hashlib.sha256(a.read_bytes()).hexdigest()=='78fb2752b87962d89556771600ca34460b3d0c01704c866a40863a1729cacf2d'
with tarfile.open(a) as tar:
 assert len(tar.getmembers())==3
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['run_protocol.json','background_capture0_worker.py','board_joint_repeats.py']
  f=root/m.name;assert not f.exists();f.write_bytes(tar.extractfile(m).read())
assert hashlib.sha256((root/'run_protocol.json').read_bytes()).hexdigest()=='a7999c756c4466dc64b426bfb041a02e557c16bbbd3189c9f4ab5b5419676f0d'
with (root/'run.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_joint_repeats.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'runs':6,'offered_slots_each':392,'same_model_full_video_PID_terminal':terminal['PID'],'new_firmware_programming':False}
(root/'launch.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
