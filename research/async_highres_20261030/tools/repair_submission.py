from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026/async_highres_20261030'
source=ROOT/'tools/reference.slurm';raw=source.read_bytes();assert b'\r\n' in raw
fixed=raw.replace(b'\r\n',b'\n');lf=ROOT/'tools/reference_lf.slurm';assert not lf.exists();lf.write_bytes(fixed)
metadata={'status':'LF_ONLY_SUBMISSION_REPAIR_BEFORE_ANY_REFERENCE_JOB','created_UTC':datetime.now(timezone.utc).isoformat(),
 'old_CRLF_script_sha256':hashlib.sha256(raw).hexdigest(),'new_LF_script_sha256':hashlib.sha256(fixed).hexdigest(),
 'inputs_model_reference_protocol_runner_or_numeric_gates_changed':False,'old_failed_submission_started_compute':False,
 'reason':'sbatch rejected DOS line endings; original staged input payload and failed submission output retained.'}
file=ROOT/'protocol/reference_submission_repair_v1.json';assert not file.exists();file.write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
script='''set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly
cd REMOTE
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json
root=Path.cwd();old=root/'tools/reference.slurm';raw=old.read_bytes();assert hashlib.sha256(raw).hexdigest()=='OLD_SHA'
target=root/'tools/reference_lf.slurm';assert not target.exists();new=raw.replace(b'\\r\\n',b'\\n');assert hashlib.sha256(new).hexdigest()=='NEW_SHA'
with target.open('xb') as f:f.write(new)
p=json.loads((root/'protocol/reference_v1.json').read_text())
for row in p['input_files']:assert hashlib.sha256((root/row['file']).read_bytes()).hexdigest()==row['sha256']
print(json.dumps({'status':'ONLY_BATCH_SCRIPT_LINE_ENDINGS_NORMALIZED_INPUTS_UNCHANGED','queries':p['query_count']}))
PY
sbatch --parsable tools/reference_lf.slurm
'''.replace('REMOTE',REMOTE).replace('OLD_SHA',metadata['old_CRLF_script_sha256']).replace('NEW_SHA',metadata['new_LF_script_sha256'])
file=ROOT/'tools/submit_repaired.sh';assert not file.exists();file.write_text(script,encoding='utf-8')
subprocess.run([sys.executable,'-X','utf8',str(PROJECT/'data_audit_20261026/tools/remote_bridge.py'),'run',str(file),'--output',str(ROOT/'evidence/reference_submit_repaired.txt')],check=True)
print(json.dumps(metadata))
