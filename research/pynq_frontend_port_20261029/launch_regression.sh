set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import tarfile,json,hashlib,subprocess,sys,os
root=Path('/home/xilinx/jupyter_notebooks/cow_research_numpy_tracker_20261029')
terminal=json.loads((root/'build_terminal.json').read_text());assert terminal['success'] and not (Path('/proc')/str(terminal['PID'])).exists()
assert not (root/'regression_launch.json').exists()
archive=root/'regression_payload.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='dad396d7691782e42d42bf788ab2a27383211c6ee03bc1b04a53a97c4fe4ed81'
with tarfile.open(archive) as tar:
 assert len(tar.getmembers())==163
 for member in tar.getmembers():
  assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
  file=(root/member.name).resolve();assert file.is_relative_to(root.resolve()) and not file.exists()
  file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(tar.extractfile(member).read())
assert hashlib.sha256((root/'board_regression_v1.json').read_bytes()).hexdigest()=='238740b28022841a91c74865d6e98fd0f1c39439995033509f88568b72a32ed1'
with (root/'regression.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-u','-B',str(root/'board_regression.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
result={'PID':child.pid,'expected_traces':90,'expected_observations':82020,'network_or_PL_actions':0}
(root/'regression_launch.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
PY
