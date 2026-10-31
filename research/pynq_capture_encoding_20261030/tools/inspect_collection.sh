set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_capture_encoding_20261030')
print(json.dumps({'periodic_PID_exists':Path('/proc/5748').exists(),
 'files':[{'file':f,'exists':(root/f).exists(),'bytes':(root/f).stat().st_size if (root/f).exists() else None} for f in ['periodic_delivery.tar.gz','periodic_manifest.json','results/terminal.json']],
 'possible_collection_processes':subprocess.run(['ps','-eo','pid,ppid,state,etimes,rss,args'],capture_output=True,text=True).stdout[-6500:]}))
PY
