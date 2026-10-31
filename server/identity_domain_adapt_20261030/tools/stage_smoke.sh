set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_domain_adapt_20261030
test ! -e smoke_job_id.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path,PurePosixPath
import tarfile,hashlib,json
r=Path.cwd();archive=r/'domain_input_v1.tar.gz'
with tarfile.open(archive)as tar:
 for member in tar.getmembers():
  relative=PurePosixPath(member.name);assert member.isfile()and not relative.is_absolute()and'..'not in relative.parts
  p=(r/member.name).resolve();assert p.is_relative_to(r)and not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(member).read())
e=json.loads((r/'protocol/execution_v1.json').read_text())
for path,digest in e['files_sha256'].items():assert hashlib.sha256((r/path).read_bytes()).hexdigest()==digest
print(json.dumps({'archive_bytes':archive.stat().st_size,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'all_input_files_verified':len(e['files_sha256'])}))
PY
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
job_id=$(sbatch --parsable tools/smoke.slurm)
printf '%s\n' "$job_id" > smoke_job_id.txt
printf 'SMOKE_JOB_ID=%s\n' "$job_id"
