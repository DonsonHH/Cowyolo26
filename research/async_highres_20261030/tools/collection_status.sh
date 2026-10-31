set -euo pipefail
test "$(id -un)" = xilinx
python3 - <<'PY'
from pathlib import Path
import json,subprocess
r=Path('/home/xilinx/jupyter_notebooks/cow_research_async_highres_20261030');l=json.loads((r/'collection_launch.json').read_text());terminal=json.loads((r/'collection_terminal.json').read_text()) if (r/'collection_terminal.json').exists() else None
print(json.dumps({'launch':l,'proc_exists':(Path('/proc')/str(l['PID'])).exists(),'ps':subprocess.run(['ps','-p',str(l['PID']),'-o','pid,state,etimes,rss,comm'],capture_output=True,text=True).stdout,'terminal':terminal,'log_tail':(r/'collection.log').read_text(errors='replace')[-1800:]}))
PY
