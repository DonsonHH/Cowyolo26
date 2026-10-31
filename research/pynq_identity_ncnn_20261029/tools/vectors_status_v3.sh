set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029');launch=json.loads((root/'vectors_v3_launch.json').read_text())
record={'launch':launch,'ps':subprocess.run(['ps','-p',str(launch['PID']),'-o','pid,state,etimes,rss,comm'],capture_output=True,text=True).stdout,
 'progress':(root/'vectors_results_v3/progress.json').read_text() if (root/'vectors_results_v3/progress.json').exists() else None,
 'terminal':(root/'vectors_results_v3/terminal.json').read_text() if (root/'vectors_results_v3/terminal.json').exists() else None,
 'log_tail':(root/'vectors_v3.log').read_text(errors='replace')[-2500:]}
print(json.dumps(record))
PY
