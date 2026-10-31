set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess,sys,os
root=Path('/home/xilinx/jupyter_notebooks/cow_research_capture_encoding_20261030');t=json.loads((root/'encoding_results/terminal.json').read_text());assert t['success'] and not (Path('/proc')/str(t['PID'])).exists()
assert not (root/'results').exists() and not (root/'periodic_launch.json').exists()
archive=root/'periodic_payload.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='b115fc04e7bb2db0d2b8f7280b7443207ff56b363c2329535fc61b6119ce4bcc'
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['run_protocol.json','board_periodic_capture0.py','background_capture0_worker.py']
  p=root/m.name;assert not p.exists();p.write_bytes(tar.extractfile(m).read())
with (root/'periodic.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_periodic_capture0.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'cases':3,'offered_slots_each':392,'actual_PNG_compress_level':0,'lossless_pixels_unchanged':True}
(root/'periodic_launch.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
