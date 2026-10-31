set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_numpy_tracker_20261029');launch=json.loads((root/'launch.json').read_text())
record={'launch':launch,'ps':subprocess.run(['ps','-p',str(launch['PID']),'-o','pid,state,etimes,rss,comm'],capture_output=True,text=True).stdout,
 'terminal':(root/'build_terminal.json').read_text() if (root/'build_terminal.json').exists() else None,
 'result':(root/'build_result.json').read_text() if (root/'build_result.json').exists() else None,
 'failure':(root/'build_failure.json').read_text() if (root/'build_failure.json').exists() else None,
 'log_tail':(root/'compile.log').read_text(errors='replace')[-1800:] if (root/'compile.log').exists() else (root/'run.log').read_text(errors='replace')[-1800:]}
print(json.dumps(record))
PY
