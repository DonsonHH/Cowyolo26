set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_joint_pair_20261030
test ! -e reference_job_id.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
r=Path.cwd();archive=r/'reference_input_v1.tar.gz';assert archive.stat().st_size==2743374 and hashlib.sha256(archive.read_bytes()).hexdigest()=='6aa98addf40900ec766320a997ecdfde1bd42c713d7b5c5ebce10a4c72a3d638'
with tarfile.open(archive)as tar:
 members=tar.getmembers();assert len(members)==5
 for row in members:
  rel=PurePosixPath(row.name);assert row.isfile()and not rel.is_absolute()and'..'not in rel.parts
  p=(r/row.name).resolve();assert p.is_relative_to(r)and not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(row).read())
e=json.loads((r/'protocol/cpu_execution_v1.json').read_text());assert hashlib.sha256((r/'protocol/cpu_reference_v1.json').read_bytes()).hexdigest()==e['protocol_sha256']
for file,digest in e['code_sha256'].items():assert hashlib.sha256((r/file).read_bytes()).hexdigest()==digest
print(json.dumps({'status':'FROZEN40_REFERENCE_INPUT_BUNDLE_VERIFIED','sha256':'6aa98addf40900ec766320a997ecdfde1bd42c713d7b5c5ebce10a4c72a3d638'}))
PY
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
job_id=$(sbatch --parsable tools/reference.slurm)
printf '%s\n' "$job_id" > reference_job_id.txt
printf 'REFERENCE_JOB_ID=%s\n' "$job_id"
