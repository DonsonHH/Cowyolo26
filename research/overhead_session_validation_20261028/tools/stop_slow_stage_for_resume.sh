set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
"$PROJECT/env/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,os,signal,subprocess
root=Path('/share/home/renly/projects/idcoo_research_20261026/overhead_session_validation_20261028')
target=str(root/'tools/stage_videos.py')
matches=[]
for line in subprocess.check_output(['ps','-u',str(os.getuid()),'-o','pid=,args='],text=True).splitlines():
    parts=line.split();args=parts[1:]
    if len(args)==2 and args[1]==target and args[0].endswith('/python'):matches.append(int(parts[0]))
record={'reason':'Verified progress was only a few MiB over several minutes; local bounded HTTPS range probe took 4.75 s for 256 KiB. Preserve prefixes and resume using local route.',
        'exact_own_stage_PIDs':matches,'deleted_files':False,'changed_proxy_or_nodes':False}
if len(matches)==1:
    os.kill(matches[0],signal.SIGTERM);record['action']='SIGTERM_exact_own_network_stage_process_for_faster_resume'
else:
    assert not matches and (root/'evidence/fetch_manifest.json').exists(),'Unexpected process state; do not signal anything'
    record['action']='already_completed_no_signal'
files=[]
for f in sorted((root/'data').glob('*/RGB.avi.partial')):
    b=f.read_bytes();files.append({'sequence':f.parent.name,'path':str(f),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
record['preserved_prefixes']=files
(root/'evidence/stage_transfer_stop.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record))
PY
