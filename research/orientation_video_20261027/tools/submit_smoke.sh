set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import json,hashlib,tarfile
project=Path('/share/home/renly/projects/idcoo_research_20261026')
archive=project/'orientation_video_20261027.staging.tar.gz'
assert archive.stat().st_size==38970 and hashlib.sha256(archive.read_bytes()).hexdigest()=='24ded49b35afc6cae6105c0dc0f6adde27b2af3325db59ef3144f459be55922a'
root=project/'orientation_video_20261027';assert not root.exists();root.mkdir()
with tarfile.open(archive) as tar:
    for item in tar:
        assert item.isfile() and (root/item.name).resolve().is_relative_to(root)
    tar.extractall(root,filter='data')
entries=json.loads((root/'input/staging_manifest.json').read_text())
for row in entries:
    path=root/row['path'];assert path.stat().st_size==row['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
    if path.suffix=='.py':compile(path.read_text(),str(path),'exec')
(root/'results').mkdir();(root/'logs').mkdir()
print(json.dumps({'staged_files_verified':len(entries),'dataset_or_weights_mutated':False}))
PY
sinfo -o '%P|%a|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%R'
stage="$project/orientation_video_20261027"
jobid=$(sbatch --parsable "$stage/tools/smoke.slurm")
printf '%s\n' "$jobid" > "$stage/results/smoke_job_id.txt"
printf '%s\n' "$jobid"
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%R'
