set -euo pipefail
test "$(id -un)" = xilinx
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json
root=Path('/home/xilinx/jupyter_notebooks/cow_research_startup_probe_20261031')
load=lambda path:json.loads(path.read_text())if path.exists()else None
launch=load(root/'launch.json');state=load(root/'results/record.json')or{}
progress=load(root/'results/progress.json')or{}
current=root/'results'/progress.get('run','_none')
print(json.dumps({'controller_PID':launch['PID'],'controller_proc_exists':(Path('/proc')/str(launch['PID'])).exists(),
 'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'terminal':load(root/'results/terminal.json'),
 'progress':progress,'current_parent_progress':load(current/'progress.json'),
 'runs':state.get('runs',[]),'log_tail':(root/'controller.log').read_text()[-1200:],
 'current_parent_log_tail':(root/'results'/(progress.get('run','_none')+'.log')).read_text()[-1200:]if(root/'results'/(progress.get('run','_none')+'.log')).exists()else None}),flush=True)
PY
