set -euo pipefail
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json
root=Path('/home/xilinx/jupyter_notebooks/cow_research_causal_photo_20261030');root.mkdir(exist_ok=False)
print(json.dumps({'status':'NEW_CAUSAL_PHOTO_TASK_DIRECTORY_CREATED','path':str(root),'forwards':0,'PL_actions':0}))
PY
