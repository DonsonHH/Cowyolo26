set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_domain_ncnn_20261030
test ! -e export_job_id.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path,PurePosixPath
import tarfile,hashlib,json
r=Path.cwd();archive=r/'export_input_v1.tar.gz'
with tarfile.open(archive)as tar:
 for member in tar.getmembers():
  path=PurePosixPath(member.name);assert member.isfile()and not path.is_absolute()and'..'not in path.parts
  p=(r/member.name).resolve();assert p.is_relative_to(r)and not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(member).read())
e=json.loads((r/'protocol/execution_v1.json').read_text())
for name,digest in e['code_hashes'].items():assert hashlib.sha256((r/'tools'/name).read_bytes()).hexdigest()==digest
print(json.dumps({'staged_archive_bytes':archive.stat().st_size,'staged_archive_SHA256':hashlib.sha256(archive.read_bytes()).hexdigest()}))
PY
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
job_id=$(sbatch --parsable tools/export.slurm)
printf '%s\n' "$job_id" > export_job_id.txt
printf 'EXPORT_JOB_ID=%s\n' "$job_id"
