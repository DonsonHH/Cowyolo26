set -euo pipefail
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json
r=Path('/home/xilinx/jupyter_notebooks/cow_research_async_highres_20261030');r.mkdir(exist_ok=False);print(json.dumps({'status':'NEW_ASYNC_HIGHRES_TASK_DIRECTORY_CREATED','path':str(r)}))
PY
