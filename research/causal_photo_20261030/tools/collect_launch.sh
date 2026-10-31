set -euo pipefail
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,subprocess,sys,os
root=Path('/home/xilinx/jupyter_notebooks/cow_research_causal_photo_20261030')
t=json.loads((root/'results/terminal.json').read_text());assert t['status']=='ALL_SIX392_SLOT_CAUSAL_PHOTO_SAME_BOARD_REPEATS_COMPLETE' and not (Path('/proc')/str(t['PID'])).exists()
assert not (root/'collection_launch.json').exists() and not (root/'collection_terminal.json').exists()
with (root/'collection.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-u',str(root/'collect_results.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'task_PID':t['PID'],'status':'COLLECTOR_LAUNCHED'};(root/'collection_launch.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
