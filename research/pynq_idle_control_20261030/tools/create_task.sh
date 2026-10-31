set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json
p=Path('/home/xilinx/jupyter_notebooks/cow_research_idle_control_20261030');p.mkdir(exist_ok=False);print(json.dumps({'created':str(p)}))
PY
