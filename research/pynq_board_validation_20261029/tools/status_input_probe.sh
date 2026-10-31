set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_validation_v2_20261029');launch=json.loads((root/'launch_input_probe.json').read_text());pid=launch['PID']
result={'launch':launch,'ps':subprocess.run(['ps','-p',str(pid),'-o','pid,state,etimes,rss,comm'],capture_output=True,text=True).stdout,
        'progress':(root/'input_probe/progress.json').read_text() if (root/'input_probe/progress.json').exists() else None,
        'terminal':(root/'input_probe/terminal.json').read_text() if (root/'input_probe/terminal.json').exists() else None,
        'log_tail':(root/'input_probe.log').read_text(errors='replace')[-1500:]}
print(json.dumps(result))
PY
