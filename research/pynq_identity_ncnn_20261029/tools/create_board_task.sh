set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json
root=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029');root.mkdir(exist_ok=False);print(json.dumps({'status':'ISOLATED_NCNN_BUILD_DIRECTORY_CREATED','path':str(root)}))
PY
