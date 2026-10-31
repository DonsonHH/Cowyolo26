set -euo pipefail
test "$(id -un)" = xilinx
python3 - <<'PY'
from pathlib import Path
import json,subprocess
r=Path('/home/xilinx/jupyter_notebooks/cow_research_input_cost_v2_20261030');l=json.loads((r/'launch.json').read_text())
print(json.dumps({'launch':l,'proc_exists':(Path('/proc')/str(l['PID'])).exists(),'ps':subprocess.run(['ps','-p',str(l['PID']),'-o','pid,state,etimes,rss,comm'],capture_output=True,text=True).stdout,'progress':json.loads((r/'results/progress.json').read_text()) if (r/'results/progress.json').exists() else None,'terminal':json.loads((r/'results/terminal.json').read_text()) if (r/'results/terminal.json').exists() else None,'log_tail':(r/'run.log').read_text(errors='replace')[-1400:]}))
PY
