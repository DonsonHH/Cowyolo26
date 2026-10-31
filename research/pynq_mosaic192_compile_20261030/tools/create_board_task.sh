set -euo pipefail
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json
root=Path('/home/xilinx/jupyter_notebooks/cow_research_o8_mosaic192_qual_20261030');root.mkdir(exist_ok=False)
print(json.dumps({'status':'NEW_MOSAIC192_/home/xilinx/jupyter_notebooks/cow_research_o8_mosaic192_qual_20261030_DIRECTORY_CREATED','root':str(root),'new_PL_or_model_actions':0}))
PY
