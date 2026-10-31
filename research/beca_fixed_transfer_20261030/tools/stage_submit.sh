set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/beca_fixed_transfer_20261030
test ! -e evaluation_job_id.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
r=Path.cwd();archive=r/'BECA_transfer_input_v1.tar.gz'
assert archive.stat().st_size==26720357 and hashlib.sha256(archive.read_bytes()).hexdigest()=='ba6192781b110e5a10320463336e30057ef382c745ac342a9cecc8e6f42269b9'
with tarfile.open(archive)as tar:
 members=tar.getmembers();assert len(members)==471
 for member in members:
  rel=PurePosixPath(member.name);assert member.isfile()and not rel.is_absolute()and'..'not in rel.parts
  path=(r/member.name).resolve();assert path.is_relative_to(r)and not path.exists()
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(member).read())
manifest=json.loads((r/'input_bundle_manifest_v1.json').read_text())
for row in manifest:
 path=r/row['file'];assert path.stat().st_size==row['bytes']and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
e=json.loads((r/'protocol/execution_v1.json').read_text())
assert hashlib.sha256((r/'protocol/run_v1.json').read_bytes()).hexdigest()==e['protocol_sha256']
for name,digest in e['files_sha256'].items():assert hashlib.sha256((r/name).read_bytes()).hexdigest()==digest
for model in e['models']:assert hashlib.sha256(Path(model['checkpoint']).read_bytes()).hexdigest()==model['checkpoint_sha256']
print(json.dumps({'status':'ALL_INPUT_FILES_AND_TWO_EXISTING_CHECKPOINT_HASHES_VERIFIED_BEFORE_FORWARD','members':len(members),'model_forwards':0}))
PY
bash -n tools/evaluation.slurm
bash -n tools/collect_final.sh
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
job_id=$(sbatch --parsable tools/evaluation.slurm)
printf '%s\n' "$job_id" > evaluation_job_id.txt
printf 'BECA_FIXED_TRANSFER_JOB_ID=%s\n' "$job_id"
