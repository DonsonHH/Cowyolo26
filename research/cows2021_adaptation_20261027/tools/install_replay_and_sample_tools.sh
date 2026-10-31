set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
stage="$project/cows2021_adaptation_20261027"
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,tarfile
project=Path('/share/home/renly/projects/idcoo_research_20261026')
root=project/'cows2021_adaptation_20261027'
archive=project/'cows2021_adaptation_20261027.replay_and_sample_tools_v1.tar.gz'
assert archive.stat().st_size==7640
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='f57b8d5238756fa486705806073d85b9b32df7ad5b938b1abb45c578e06ce72b'
with tarfile.open(archive) as tf:
    for member in tf:
        p=root/member.name
        assert member.isfile() and p.resolve().is_relative_to(root) and not p.exists()
    tf.extractall(root,filter='data')
rows=json.loads((root/'results/replay_and_sample_tools_v1.json').read_text())
for row in rows:
    p=root/row['path'];assert p.is_file() and p.stat().st_size==row['bytes']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
    if p.suffix=='.py':compile(p.read_text(),str(p),'exec')
print(json.dumps({'files_verified':len(rows),'replay_or_training_started':False}))
PY
sinfo -o '%P|%a|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable "$stage/tools/sample_loader.slurm")
printf '%s\n' "$jobid"
printf '%s\n' "$jobid" > "$stage/results/sample_loader64_job_id.txt"
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
