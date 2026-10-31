set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json
root=Path('/home/xilinx/jupyter_notebooks/cow_research_periodic_joint_20261030');root.mkdir(exist_ok=False);print(json.dumps({'status':'NEW_PERIODIC_JOINT_TASK_DIRECTORY_CREATED','path':str(root)}))
PY
