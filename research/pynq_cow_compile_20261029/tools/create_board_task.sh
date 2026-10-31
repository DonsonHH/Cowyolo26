set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json
root=Path('/home/xilinx/jupyter_notebooks/cow_research_o8_cow_qual_20261029');root.mkdir(exist_ok=False)
print(json.dumps({'status':'NEW_COW_O8_QUALIFICATION_TASK_DIRECTORY_CREATED','root':str(root),'board_model_or_PL_actions':0}))
PY
