set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json
root=Path('/home/xilinx/jupyter_notebooks/cow_research_numpy_tracker_20261029');root.mkdir(exist_ok=False)
print(json.dumps({'status':'ISOLATED_NUMPY_TRACKER_BUILD_DIRECTORY_CREATED','path':str(root),'model_or_PL_actions':0}))
PY
