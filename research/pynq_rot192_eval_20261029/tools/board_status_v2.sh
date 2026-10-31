set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_rot192_video_20261029');launch=json.loads((root/'launch_v2.json').read_text())
record={'launch':launch,'ps':subprocess.run(['ps','-p',str(launch['PID']),'-o','pid,state,etimes,rss,comm'],capture_output=True,text=True).stdout,
 'progress':(root/'results_v2/progress.json').read_text() if (root/'results_v2/progress.json').exists() else None,
 'terminal':(root/'results_v2/terminal.json').read_text() if (root/'results_v2/terminal.json').exists() else None,
 'log_tail':(root/'run_v2.log').read_text(errors='replace')[-1500:]}
print(json.dumps(record))
PY
