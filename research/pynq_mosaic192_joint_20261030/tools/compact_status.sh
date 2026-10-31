set -euo pipefail
python3 - <<'PY'
from pathlib import Path
import json
r=Path('/home/xilinx/jupyter_notebooks/cow_research_mosaic192_joint_20261030')
launch=json.loads((r/'launch.json').read_text());pid=launch['PID']
print(json.dumps({'PID':pid,'proc_exists':(Path('/proc')/str(pid)).exists(),
 'progress':json.loads((r/'results/progress.json').read_text()) if (r/'results/progress.json').exists() else None,
 'terminal':json.loads((r/'results/terminal.json').read_text()) if (r/'results/terminal.json').exists() else None,
 'completed_runs':[{k:c[k] for k in ['run','processed_frames','skipped_slots','deadline_misses','source_down_count','actual_background_jobs']} for c in json.loads((r/'results/record.json').read_text()).get('cases',[])] if (r/'results/record.json').exists() else []}))
PY
