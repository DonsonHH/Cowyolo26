set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_joint_pair_20261030
test ! -e tracker_job_id.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
r=Path.cwd();a=r/'tracker_input_v1.tar.gz';assert a.stat().st_size==5250712 and hashlib.sha256(a.read_bytes()).hexdigest()=='2b4a4b1e479d77f982faa01b9dbed6f6d959f833d7bf6f60feac300fef8e5b6e'
with tarfile.open(a)as tar:
 members=tar.getmembers();assert len(members)==22
 for row in members:
  rel=PurePosixPath(row.name);assert row.isfile()and not rel.is_absolute()and'..'not in rel.parts;p=(r/row.name).resolve();assert p.is_relative_to(r)and not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(row).read())
p=json.loads((r/'tracker_input/protocol.json').read_text())
for row in p['files']:assert hashlib.sha256((r/row['file']).read_bytes()).hexdigest()==row['sha256']
print(json.dumps({'status':'FULL4_TRACKER_REPLAY_INPUT_CODE_AND_ARCHIVE_SHA_VERIFIED','new_model_forwards':0}))
PY
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
job_id=$(sbatch --parsable tools/tracker_replay.slurm)
printf '%s\n' "$job_id" > tracker_job_id.txt
printf 'TRACKER_JOB_ID=%s\n' "$job_id"
