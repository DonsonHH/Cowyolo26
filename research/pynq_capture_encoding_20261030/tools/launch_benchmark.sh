set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess,os,sys
root=Path('/home/xilinx/jupyter_notebooks/cow_research_capture_encoding_20261030');old=Path('/home/xilinx/jupyter_notebooks/cow_research_idle_control_20261030');t=json.loads((old/'results/terminal.json').read_text());assert not (Path('/proc')/str(t['PID'])).exists()
archive=root/'benchmark_payload.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='cc01fa39ad40cf8f6402ec06a77605b6c9ac36df43a3d46330100e16ee0e1ed9'
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['protocol.json','board_benchmark.py']
  p=root/m.name;assert not p.exists();p.write_bytes(tar.extractfile(m).read())
with (root/'benchmark.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-u','-B',str(root/'board_benchmark.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'photo_encodes':22,'actual_model_forwards':0};(root/'benchmark_launch.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
