set -euo pipefail
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json
root=Path('/home/xilinx/jupyter_notebooks/cow_research_mosaic192_joint_20261030');root.mkdir(exist_ok=False);print(json.dumps({'status':'NEW_JOINT_REPEATS_DIRECTORY_CREATED','path':str(root),'new_model_or_PL_actions':0}))
PY
