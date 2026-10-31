set -euo pipefail
test "$(id -un)" = xilinx
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json
root=Path('/home/xilinx/jupyter_notebooks/cow_research_startup_probe_20261031')
load=lambda path:json.loads(path.read_text())if path.exists()else None
launch=load(root/'collection_launch.json')
print(json.dumps({'collector_PID':launch['PID'],'collector_proc_exists':(Path('/proc')/str(launch['PID'])).exists(),
 'transfer':load(root/'transfer.json'),'log_tail':(root/'collection.log').read_text()[-1500:]}),flush=True)
PY
