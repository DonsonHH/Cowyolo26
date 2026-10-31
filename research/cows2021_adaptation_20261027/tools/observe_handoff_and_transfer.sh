set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
"$project/env/bin/python" - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import os,json,subprocess
root=Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
processes=[]
for pid,expected in [(2794954,'fetch_images.py'),(219725,'after_download_audit.py')]:
    p=Path('/proc')/str(pid);command=None;live=False
    try:
        command=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode().strip()
        live=p.stat().st_uid==os.getuid() and str(root/'tools'/expected) in command
    except (FileNotFoundError,ProcessLookupError):pass
    state=subprocess.run(['ps','-p',str(pid),'-o','pid,lstart,etime,state,args'],capture_output=True,text=True)
    processes.append({'PID':pid,'expected_script':expected,'live_owned_expected_process':live,
                      'command':command,'ps':state.stdout.strip()})
def read(relative):
    p=root/relative
    return json.loads(p.read_text()) if p.exists() else None
files=list((root/'raw_images').rglob('*.jpg'))
value={'observed_UTC':datetime.now(timezone.utc).isoformat(),'processes':processes,
       'progress':read('results/download_attempt_01/progress.json'),
       'transfer_terminal':read('results/download_attempt_01/summary.json'),
       'handoff_terminal':read('results/download_handoff_01/summary.json'),
       'saved_JPEG_files':len(files),'saved_JPEG_bytes':sum(p.stat().st_size for p in files)}
print(json.dumps(value),flush=True)
PY
