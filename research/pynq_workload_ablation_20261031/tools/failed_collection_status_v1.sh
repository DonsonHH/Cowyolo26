set -euo pipefail
test "$(id -un)" = xilinx
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json
root=Path('/home/xilinx/jupyter_notebooks/cow_research_workload_ablation_20261031')
launch=json.loads((root/'failed_collection_launch_v1.json').read_text())
print(json.dumps({'PID':launch['PID'],'proc_exists':(Path('/proc')/str(launch['PID'])).exists(),
 'transfer':json.loads((root/'failure_transfer_v1.json').read_text())if(root/'failure_transfer_v1.json').exists()else None,
 'final':json.loads((root/'failed_final_state_v1.json').read_text())if(root/'failed_final_state_v1.json').exists()else None,
 'log_tail':(root/'failed_collection_v1.log').read_text()[-1000:]}),flush=True)
PY
