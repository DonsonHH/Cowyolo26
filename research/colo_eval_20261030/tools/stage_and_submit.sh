set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/colo_eval_20261030
test ! -e results/evaluation
test ! -e submission.json
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path, PurePosixPath
import json,hashlib,tarfile,subprocess
root=Path.cwd();archive=root/'colo_input_v1.tar.gz'
with tarfile.open(archive) as tar:
 for member in tar.getmembers():
  relative=PurePosixPath(member.name)
  assert member.isfile() and not relative.is_absolute() and '..' not in relative.parts
  dest=(root/member.name).resolve();assert dest.is_relative_to(root) and not dest.exists()
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(tar.extractfile(member).read())
plan=json.loads((root/'protocol/run_v1.json').read_text());execution=json.loads((root/'protocol/execution_v1.json').read_text())
for relative,digest in execution['files_sha256'].items():assert hashlib.sha256((root/relative).read_bytes()).hexdigest()==digest
wheel=root/'input'/plan['evaluation_library']['wheel'];assert hashlib.sha256(wheel.read_bytes()).hexdigest()==plan['evaluation_library']['sha256']
subprocess.run(['/share/home/renly/projects/idcoo_research_20261026/env/bin/python','-m','pip','install','--no-index','--no-deps','--target',str(root/'vendor'),str(wheel)],check=True)
print(json.dumps({'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'package_installed_only_task_vendor':True,'input_files_verified':len(execution['files_sha256'])}))
PY
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
job_id=$(sbatch --parsable tools/evaluate.slurm)
printf '%s\n' "$job_id" > submitted_job_id.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json
p=Path('submission.json');assert not p.exists()
value={'Slurm_job_id':Path('submitted_job_id.txt').read_text().strip(),'created_UTC':datetime.now(timezone.utc).isoformat(),'own_job_only':True}
p.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))
PY
