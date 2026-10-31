set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_o8_rot192_qual_20261029');launch=json.loads((root/'launch.json').read_text());pid=launch['PID']
record={'launch':launch,'ps':subprocess.run(['ps','-p',str(pid),'-o','pid,state,etimes,rss,comm'],capture_output=True,text=True).stdout,
   'progress':(root/'results/progress.json').read_text() if (root/'results/progress.json').exists() else None,
   'terminal':(root/'results/terminal.json').read_text() if (root/'results/terminal.json').exists() else None,
   'log_tail':(root/'run.log').read_text(errors='replace')[-2000:]}
print(json.dumps(record))
PY
