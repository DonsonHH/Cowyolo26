set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/cows2021_identity_eval_20261030
test ! -e results/evaluation
test ! -e submission.json
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path,PurePosixPath
import tarfile,json,hashlib
r=Path.cwd();a=r/'identity_input_v1.tar.gz'
with tarfile.open(a) as tar:
 for member in tar.getmembers():
  path=PurePosixPath(member.name);assert member.isfile() and not path.is_absolute() and '..' not in path.parts
  p=(r/member.name).resolve();assert p.is_relative_to(r) and not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(member).read())
e=json.loads((r/'protocol/execution_v1.json').read_text())
for relative,digest in e['files_sha256'].items():assert hashlib.sha256((r/relative).read_bytes()).hexdigest()==digest
print(json.dumps({'archive_bytes':a.stat().st_size,'archive_sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'staged_files_verified':len(e['files_sha256'])}))
PY
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
job_id=$(sbatch --parsable tools/identity_evaluation.slurm)
printf '%s\n' "$job_id" > submitted_job_id.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json
record={'Slurm_job_id':Path('submitted_job_id.txt').read_text().strip(),'created_UTC':datetime.now(timezone.utc).isoformat(),'own_job_only':True}
p=Path('submission.json');assert not p.exists();p.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
PY
