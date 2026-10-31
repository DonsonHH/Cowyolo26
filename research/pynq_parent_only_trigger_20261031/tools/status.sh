set -euo pipefail
test "$(id -un)" = xilinx
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json
root=Path('/home/xilinx/jupyter_notebooks/cow_research_parent_only_trigger_20261031')
load=lambda p:json.loads(p.read_text())if p.exists()else None
launch=load(root/'launch.json');state=load(root/'results/record.json')or{}
print(json.dumps({'PID':launch['PID'],'proc_exists':(Path('/proc')/str(launch['PID'])).exists(),
 'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'terminal':load(root/'results/terminal.json'),
 'progress':load(root/'results/progress.json'),'state_status':state.get('status'),'error':state.get('error'),
 'cases':[{key:case[key]for key in['run','identity_model','processed_frames','skipped_slots','deadline_misses','processed_per_second_over_offered_duration','P95_release_to_count_ms','source_down_count','actual_background_jobs']}for case in state.get('cases',[])],
 'log_tail':(root/'run.log').read_text()[-1000:]}),flush=True)
PY
