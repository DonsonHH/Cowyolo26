set -euo pipefail
test "$(id -un)" = xilinx
python3 - <<'PY'
from pathlib import Path
import json
root=Path('/home/xilinx/jupyter_notebooks/cow_research_mosaic192_video_20261030')
files={name:(root/name).read_text(errors='replace')[-4000:] if (root/name).exists() else None for name in ['launch.json','results/progress.json','results/terminal.json','run.log']}
processes=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  args=(proc/'cmdline').read_bytes().split(b'\0')
  if any(b'cow_research_mosaic192_video_20261030' in arg for arg in args):
   processes.append({'PID':int(proc.name),'argv_prefix':[a.decode('utf-8','replace')[:200] for a in args[:4]],'proc_exists':True})
 except (FileNotFoundError,ProcessLookupError,PermissionError):pass
print(json.dumps({'files':files,'processes':processes,'extracted_PNG_count':sum(1 for f in (root/'board_inputs').rglob('*.png')),'board_protocol_exists':(root/'board_protocol.json').exists(),'new_model_or_launch_actions':0}))
PY
