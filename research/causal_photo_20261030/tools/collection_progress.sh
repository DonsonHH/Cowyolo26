set -euo pipefail
test "$(id -un)" = xilinx
python3 - <<'PY'
from pathlib import Path
import json,subprocess
r=Path('/home/xilinx/jupyter_notebooks/cow_research_causal_photo_20261030');l=json.loads((r/'collection_launch.json').read_text());pid=l['PID'];a=r/'causal_photo_delivery_v1.tar.gz'
print(json.dumps({'PID':pid,'proc_exists':(Path('/proc')/str(pid)).exists(),'ps':subprocess.run(['ps','-p',str(pid),'-o','pid,state,etimes,time,rss,comm'],capture_output=True,text=True).stdout,'archive_bytes_so_far_not_complete':a.stat().st_size if a.exists() else None,'terminal':json.loads((r/'collection_terminal.json').read_text()) if (r/'collection_terminal.json').exists() else None}))
PY
