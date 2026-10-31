set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_validation_v2_20261029');launch=json.loads((root/'launch_framebank_replay.json').read_text());pid=launch['PID']
result={'launch':launch,'ps':subprocess.run(['ps','-p',str(pid),'-o','pid,state,etimes,rss,comm'],capture_output=True,text=True).stdout,
        'progress':(root/'framebank_replay/progress.json').read_text() if (root/'framebank_replay/progress.json').exists() else None,
        'terminal':(root/'framebank_replay/terminal.json').read_text() if (root/'framebank_replay/terminal.json').exists() else None,
        'log_tail':(root/'framebank_replay.log').read_text(errors='replace')[-1200:]}
print(json.dumps(result))
PY
