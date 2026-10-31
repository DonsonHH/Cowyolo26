set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OPENBLAS_NUM_THREADS=2
export OMP_NUM_THREADS=2
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,tarfile,hashlib,subprocess,sys,os
root=Path('/home/xilinx/jupyter_notebooks/cow_research_o8_s320_qual_20261030')
old=json.loads((root/'launch.json').read_text());assert old['PID']==10019 and not Path('/proc/10019').exists()
assert not list((root/'results').iterdir()) and not (root/'results_v2').exists()
archive=root/'repair_patch.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='f992d155075fa12f83bba4d0e7fe5e242e69a68badf2e4444cdf3bd4bdb6628e'
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['board_s320_vectors_v2.py','protocol_v2.json']
  p=root/m.name;assert not p.exists();p.write_bytes(tar.extractfile(m).read())
with (root/'run_v2.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_s320_vectors_v2.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'size':320,'expected_model_forwards':10,'legacy_numpy_reference_failure_preserved':True,'ordered_reference_qualified':True}
(root/'launch_v2.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
