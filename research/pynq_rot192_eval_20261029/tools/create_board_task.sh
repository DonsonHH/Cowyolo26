set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json
p=Path('/home/xilinx/jupyter_notebooks/cow_research_rot192_video_20261029');p.mkdir(exist_ok=False);print(json.dumps({'status':'ACTUAL_VIDEO_TASK_DIRECTORY_CREATED','path':str(p),'model_or_PL_actions':0}))
PY
