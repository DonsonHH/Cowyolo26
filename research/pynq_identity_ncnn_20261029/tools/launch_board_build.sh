set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import tarfile,json,hashlib,subprocess,sys,os
root=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029');archive=root/'build_payload.tar.gz'
video=Path('/home/xilinx/jupyter_notebooks/cow_research_rot192_video_20261029')
t=json.loads((video/'results_v2/terminal.json').read_text());assert t['status']=='ALL2654_ACTUAL_O8_VIDEO_INPUTS_AND_REAL_ARM_COUNTER_PATHS_COMPLETE' and not (Path('/proc')/str(t['PID'])).exists()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='38cd1ce694b0324949781008f283ecfce3c3af0f38d7e60caf276bbb7f36bcdf'
assert not (root/'launch.json').exists()
with tarfile.open(archive) as tar:
 assert len(tar.getmembers())==6
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(root/m.name).resolve();assert p.is_relative_to(root.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
with (root/'run.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-u','-B',str(root/'build_ncnn_board.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
record={'PID':child.pid,'build_parallelism':1,'global_dependency_changes':False,'model_or_PL_actions':0,'prior_foreground_replay_terminated':True}
(root/'launch.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
PY
