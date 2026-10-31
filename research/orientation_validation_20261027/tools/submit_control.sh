set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,tarfile
project=Path('/share/home/renly/projects/idcoo_research_20261026')
archive=project/'orientation_validation_20261027.staging.tar.gz'
assert archive.stat().st_size==2615650
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='f7e4db4469c70fcafe615ecbaf0d3509817aaedbd2187dacb5e49bc4ad60987e'
root=project/'orientation_validation_20261027';assert not root.exists();root.mkdir()
with tarfile.open(archive) as tf:
    for member in tf:
        assert member.isfile() and (root/member.name).resolve().is_relative_to(root)
    tf.extractall(root,filter='data')
entries=json.loads((root/'input/staging_manifest.json').read_text())
for row in entries:
    path=root/row['path'];assert path.stat().st_size==row['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
    if path.suffix=='.py':compile(path.read_text(),str(path),'exec')
(root/'logs').mkdir();(root/'results').mkdir()
print(json.dumps({'staged_files_verified':len(entries),'protocol_sha256':hashlib.sha256((root/'protocol/orientation_v1.json').read_bytes()).hexdigest(),
                  'new_training_or_prediction_in_staging':False}))
PY
sinfo -o '%P|%a|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
stage="$project/orientation_validation_20261027"
jobid=$(sbatch --parsable "$stage/tools/control.slurm")
printf '%s\n' "$jobid" > "$stage/results/control_job_id.txt"
printf '%s\n' "$jobid"
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
