set -euo pipefail
test "$(id -un)" = xilinx
python3 - <<'PY'
from pathlib import Path
import json,subprocess
r=Path('/home/xilinx/jupyter_notebooks/cow_research_async_highres_20261030');l=json.loads((r/'launch.json').read_text());cases=json.loads((r/'results/record.json').read_text()).get('cases',[]) if (r/'results/record.json').exists() else []
print(json.dumps({'PID':l['PID'],'proc_exists':(Path('/proc')/str(l['PID'])).exists(),'ps':subprocess.run(['ps','-p',str(l['PID']),'-o','pid,state,etimes,rss,nlwp,comm'],capture_output=True,text=True).stdout,'progress':json.loads((r/'results/progress.json').read_text()) if (r/'results/progress.json').exists() else None,'terminal':json.loads((r/'results/terminal.json').read_text()) if (r/'results/terminal.json').exists() else None,'cases':[{k:c[k] for k in ['run','processed_frames','skipped_slots','deadline_misses','source_down_count','actual_background_jobs','producer_read_frames','producer_thread_terminal']} for c in cases],'log_tail':(r/'run.log').read_text(errors='replace')[-700:]}))
PY
