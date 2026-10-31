set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/pynq_parent_only_workload_20261031
test ! -e tracker_job_id.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path, PurePosixPath
import hashlib, json, tarfile
root=Path.cwd();archive=root/'tracker_input_v1.tar.gz'
assert archive.stat().st_size==10438322
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='39d98c7e675f4b456c6123e3913b95ec51bc24348e75903fe47854ef5a20c12d'
with tarfile.open(archive) as tar:
 members=tar.getmembers();assert len(members)==len({m.name for m in members})==33
 for member in members:
  rel=PurePosixPath(member.name)
  assert member.isfile() and not rel.is_absolute() and '..' not in rel.parts
  path=(root/member.name).resolve();assert path.is_relative_to(root) and not path.exists()
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(member).read())
plan=json.loads((root/'tracker_input/protocol.json').read_text())
assert len(plan['cases'])==8 and plan['model_forwards']==0
for row in plan['files']:
 assert hashlib.sha256((root/row['file']).read_bytes()).hexdigest()==row['sha256']
import numpy, scipy, lap, cv2, matplotlib
print(json.dumps({'status':'EIGHT_ACTUAL_SCHEDULES_AND_CODE_HASHES_OFFLINE_ENV_VERIFIED','new_model_forwards':0,
                  'numpy':numpy.__version__,'matplotlib':matplotlib.__version__}),flush=True)
PY
bash -n tools/tracker_replay.slurm
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
tracker_job_id=$(sbatch --parsable tools/tracker_replay.slurm)
printf '%s\n' "$tracker_job_id" > tracker_job_id.txt
printf 'TRACKER_JOB_ID=%s\n' "$tracker_job_id"
