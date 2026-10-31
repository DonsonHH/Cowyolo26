set -euo pipefail
test "$(id -un)" = xilinx
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json
root=Path('/home/xilinx/jupyter_notebooks/cow_research_workload_ablation_20261031')
launch=json.loads((root/'collection_launch.json').read_text());pid=launch['PID'];proc=Path('/proc')/str(pid)
print(json.dumps({'PID':pid,'proc_exists':proc.exists(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  'transfer':json.loads((root/'transfer.json').read_text())if(root/'transfer.json').exists()else None,
                  'log_tail':(root/'collection.log').read_text()[-1800:]}),flush=True)
PY
