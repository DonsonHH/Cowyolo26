set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_final20_20261030
test ! -e evaluation_job_id.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
r=Path.cwd();archive=r/'final20_input_v1.tar.gz';assert archive.stat().st_size==3142456 and hashlib.sha256(archive.read_bytes()).hexdigest()=='f2a763adb1127570dce266d411a0d57e6e5a1066d1694f239e5ec399bf61693a'
with tarfile.open(archive)as tar:
 members=tar.getmembers();assert len(members)==106
 for row in members:
  rel=PurePosixPath(row.name);assert row.isfile()and not rel.is_absolute()and'..'not in rel.parts
  p=(r/row.name).resolve();assert p.is_relative_to(r)and not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(row).read())
e=json.loads((r/'protocol/execution_v1.json').read_text());assert hashlib.sha256((r/'protocol/run_v1.json').read_bytes()).hexdigest()==e['protocol_sha256']
for file,digest in e['files_sha256'].items():assert hashlib.sha256((r/file).read_bytes()).hexdigest()==digest
print(json.dumps({'status':'FROZEN90_FINAL_IMAGES_AND_CODE_BUNDLE_SHA_VERIFIED_BEFORE_CPU_FORWARD','new_model_forwards':0}))
PY
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
job_id=$(sbatch --parsable tools/evaluation.slurm)
printf '%s\n' "$job_id" > evaluation_job_id.txt
printf 'FINAL20_EVALUATION_JOB_ID=%s\n' "$job_id"
