set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess,sys,os
root=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029')
t=json.loads((root/'build_terminal.json').read_text());assert t['success'] and not (Path('/proc')/str(t['PID'])).exists()
assert not (root/'vectors_launch.json').exists() and not (root/'vectors_results').exists()
archive=root/'vectors_payload.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='e40a907225de7b36d725cd6843441d99f8912d090fce52b98aaa33fa376bb83a'
with tarfile.open(archive) as tar:
 assert len(tar.getmembers())==270
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(root/m.name).resolve();assert p.is_relative_to(root.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
assert hashlib.sha256((root/'vectors_protocol.json').read_bytes()).hexdigest()=='3c6ef75b9dfb75cb55f2fc262e3094d7f4f07fd3636e67ad38a4fdf9bf9c4f60'
with (root/'vectors.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-u','-B',str(root/'board_vectors.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
record={'PID':child.pid,'expected_actual_vectors':132,'warmups':2,'PL_actions':0}
(root/'vectors_launch.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
PY
