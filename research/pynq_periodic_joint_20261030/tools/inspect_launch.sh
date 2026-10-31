set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_periodic_joint_20261030')
r={'launch':(root/'launch.json').read_text() if (root/'launch.json').exists() else None,
 'processes':subprocess.run(['pgrep','-af','board_periodic|background_worker|bash -s|python3 -'],capture_output=True,text=True).stdout,
 'root_files':sorted(p.name for p in root.iterdir()),'camera_JPEGs':len(list((root/'camera/highres').glob('*.jpg'))),
 'results':sorted(p.name for p in (root/'results').iterdir()) if (root/'results').exists() else None,
 'progress':(root/'results/progress.json').read_text() if (root/'results/progress.json').exists() else None,
 'log_tail':(root/'run.log').read_text(errors='replace')[-2000:] if (root/'run.log').exists() else None,
 'terminal':(root/'results/terminal.json').read_text() if (root/'results/terminal.json').exists() else None}
print(json.dumps(r))
PY
