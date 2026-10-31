set -euo pipefail
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json
r=Path('/home/xilinx/jupyter_notebooks/cow_research_input_cost_20261030');r.mkdir(exist_ok=False);print(json.dumps({'status':'NEW_INPUT_COST_TASK_DIRECTORY_CREATED','path':str(r)}))
PY
