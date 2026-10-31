set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,subprocess,os
project=Path('/share/home/renly/projects/idcoo_research_20261026')
root=project/'cows2021_adaptation_20261027'
script=root/'tools/after_download_audit.py';compile(script.read_text(),str(script),'exec')
assert not (root/'results/download_handoff_01').exists()
assert not (root/'results/download_handoff_launch_01.json').exists()
proc=Path('/proc/2794954');assert proc.exists() and proc.stat().st_uid==os.getuid()
command=(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode()
assert str(root/'tools/fetch_images.py') in command and '--attempt 01' in command
args=[str(project/'env/bin/python'),'-u',str(script),'--download-pid','2794954',
      '--download-attempt','01','--audit-attempt','01','--handoff','01']
with (root/'logs/download-handoff-01.log').open('xb') as log:
    process=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
                             cwd=root,start_new_session=True)
record={'PID':process.pid,'command':args,'code_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),
        'observed_existing_transfer_PID':2794954,'wait_deadline_s':7200,
        'allowed_next_stage':'CPU image audit only after complete byte transfer','training_submitted':False}
(root/'results/download_handoff_launch_01.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record),flush=True)
PY
