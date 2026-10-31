set -euo pipefail
test "$(id -un)" = xilinx
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json
root=Path('/home/xilinx/jupyter_notebooks/cow_research_workload_ablation_20261031')
launch=json.loads((root/'launch.json').read_text());pid=launch['PID'];proc=Path('/proc')/str(pid)
state=json.loads((root/'results/record.json').read_text())if(root/'results/record.json').exists()else{}
terminal=json.loads((root/'results/terminal.json').read_text())if(root/'results/terminal.json').exists()else None
print(json.dumps({'status':'SAME_EIGHT_CASE_TASK_OBSERVATION','PID':pid,'proc_exists':proc.exists(),
 'proc_stat':(proc/'stat').read_text()if(proc/'stat').exists()else None,
 'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'original_boot':launch['boot_id'],
 'terminal':terminal,'progress':json.loads((root/'results/progress.json').read_text())if(root/'results/progress.json').exists()else None,
 'state_status':state.get('status'),'cases':[{k:c[k]for k in['run','condition','processed_frames','skipped_slots','deadline_misses','processed_per_second_over_offered_duration','source_down_count','actual_background_jobs','actual_producer_frames']}for c in state.get('cases',[])],
 'log_tail':(root/'run.log').read_text()[-1800:]}),flush=True)
PY
