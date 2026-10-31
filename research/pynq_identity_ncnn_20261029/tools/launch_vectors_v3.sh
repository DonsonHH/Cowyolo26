set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess,sys,os
root=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029')
t=json.loads((root/'vectors_results_v2/terminal.json').read_text());assert t['status']=='FAILED' and t['model_forwards']==4 and not (Path('/proc')/str(t['PID'])).exists()
assert not (root/'vectors_results_v3').exists() and not (root/'vectors_v3_launch.json').exists()
archive=root/'vectors_v3_patch.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='f92a5ee26cf3fa108028b709c3769552db0c6602baf706ec380ccc57af4ba50c'
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['ncnn_encoder_v3.py','board_vectors_v3.py','vectors_protocol_v3.json']
  path=root/m.name;assert not path.exists();path.write_bytes(tar.extractfile(m).read())
with (root/'vectors_v3.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_vectors_v3.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'expected_vectors':132,'warmups':2,'all132_photo_inputs_prechecked_before_model':True,'prior_failed_results_retained':True}
(root/'vectors_v3_launch.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
