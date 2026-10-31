set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_trigger_pair_20261030
test ! -e verification_job_id.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
root=Path.cwd();archive=root/'verification_input_v1.tar.gz'
assert archive.stat().st_size==15738464 and hashlib.sha256(archive.read_bytes()).hexdigest()=='15bc4a90db4c45739c363a182046edf11494dd26d10020b447fa17c3901e31ce'
with tarfile.open(archive)as tar:
 members=tar.getmembers();assert len(members)==85 and len({r.name for r in members})==85
 for member in members:
  rel=PurePosixPath(member.name);assert member.isfile()and not rel.is_absolute()and'..'not in rel.parts
  path=(root/member.name).resolve();assert path.is_relative_to(root)and not path.exists()
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(member).read())
p=json.loads((root/'protocol/reference_v1.json').read_text())
e=json.loads((root/'protocol/reference_execution_v1.json').read_text())
assert hashlib.sha256((root/'protocol/reference_v1.json').read_bytes()).hexdigest()==e['protocol_sha256']
for name,digest in e['code_sha256'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
for row in p['files']:assert hashlib.sha256((root/row['file']).read_bytes()).hexdigest()==row['sha256']
for model in p['models']:assert hashlib.sha256(Path(model['checkpoint']).read_bytes()).hexdigest()==model['checkpoint_sha256']
print(json.dumps({'status':'ACTUAL35JOBS29UNIQUE_MODEL_INPUTS_AND89_EXPECTED_CPU_FORWARD_REFERENCE_VERIFIED_BEFORE_RUN','new_model_forwards':0}))
PY
bash -n tools/reference.slurm
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
job_id=$(sbatch --parsable tools/reference.slurm)
printf '%s\n' "$job_id" > verification_job_id.txt
printf 'TRIGGER_VERIFICATION_JOB_ID=%s\n' "$job_id"
