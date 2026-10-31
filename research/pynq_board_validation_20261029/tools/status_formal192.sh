set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_validation_v2_20261029')
launch=json.loads((root/'launch_formal192.json').read_text());pid=launch['PID']
report={'launch':launch,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'process':subprocess.run(['ps','-p',str(pid),'-o','pid,ppid,state,etimes,rss,comm'],capture_output=True,text=True).stdout,
        'progress':(root/'formal192/progress.json').read_text() if (root/'formal192/progress.json').exists() else None,
        'terminal':(root/'formal192/terminal.json').read_text() if (root/'formal192/terminal.json').exists() else None,
        'log_tail':(root/'formal192.log').read_text(errors='replace')[-4000:]}
print(json.dumps(report))
PY
