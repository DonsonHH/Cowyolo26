set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029');launch=json.loads((root/'launch.json').read_text());logs=sorted(root.glob('stage_*.log'))
result={'launch':launch,'ps':subprocess.run(['ps','-p',str(launch['PID']),'-o','pid,state,etimes,rss,comm'],capture_output=True,text=True).stdout,
 'terminal':(root/'build_terminal.json').read_text() if (root/'build_terminal.json').exists() else None,
 'result':(root/'build_result.json').read_text() if (root/'build_result.json').exists() else None,
 'failure':(root/'build_failure.json').read_text() if (root/'build_failure.json').exists() else None,
 'last_stage':logs[-1].name if logs else None,'last_log_tail':logs[-1].read_text(errors='replace')[-2300:] if logs else (root/'run.log').read_text(errors='replace')[-2300:]}
print(json.dumps(result))
PY
