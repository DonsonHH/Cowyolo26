set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import os,sys,json,hashlib,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_numpy_tracker_20261029');assert not (root/'launch.json').exists()
assert hashlib.sha256((root/'build_lap_board.py').read_bytes()).hexdigest()=='212ab0b8019141780ebb26d6b346cf1f4f47a3769670663946776b9cd5a3f643'
assert hashlib.sha256((root/'lap-0.5.13.tar.gz').read_bytes()).hexdigest()=='9eff7169e3ca452995af0493cc20d35452c4bfd06122c36c06457119ffbd411b'
with (root/'run.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-u','-B',str(root/'build_lap_board.py')],stdout=log,stderr=subprocess.STDOUT,cwd=root,env=os.environ.copy(),start_new_session=True)
result={'PID':child.pid,'task':'Isolated LAP0.5.13 source build','model_or_PL_actions':0}
(root/'launch.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
PY
