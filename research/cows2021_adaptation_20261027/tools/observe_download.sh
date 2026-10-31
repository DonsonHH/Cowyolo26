set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
"$project/env/bin/python" - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import os,json,socket,subprocess
root=Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
pid=2794954;proc=Path('/proc')/str(pid);command=None;owned=False
if proc.exists():
    try:
        command=proc.joinpath('cmdline').read_bytes().replace(b'\0',b' ').decode().strip()
        owned=proc.stat().st_uid==os.getuid() and str(root/'tools/fetch_images.py') in command and '--attempt 01' in command
    except (FileNotFoundError,ProcessLookupError):pass
ps=subprocess.run(['ps','-p',str(pid),'-o','pid,lstart,etime,state,args'],text=True,capture_output=True)
progress=root/'results/download_attempt_01/progress.json'
summary=root/'results/download_attempt_01/summary.json'
files=list((root/'raw_images').rglob('*.jpg'))
value={'observed_UTC':datetime.now(timezone.utc).isoformat(),'host':socket.gethostname(),
       'PID':pid,'live_owned_transfer_process':owned,'native_command':command,'native_ps':ps.stdout.strip(),
       'progress':json.loads(progress.read_text()) if progress.exists() else None,
       'transfer_terminal_summary':json.loads(summary.read_text()) if summary.exists() else None,
       'saved_JPEG_files':len(files),'saved_JPEG_bytes':sum(p.stat().st_size for p in files),
       'image_audit_summary_exists':(root/'results/image_audit_01/summary.json').exists(),
       'actual_label_loader_summary_exists':(root/'results/labels_v1/summary.json').exists(),
       'formal_training_summary_exists':(root/'results/training/summary.json').exists()}
print(json.dumps(value),flush=True)
PY
