set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
stage="$project/cows2021_adaptation_20261027"
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,tarfile,shutil
project=Path('/share/home/renly/projects/idcoo_research_20261026')
root=project/'cows2021_adaptation_20261027'
archive=project/'cows2021_adaptation_20261027.training_tools_v1.tar.gz'
assert archive.stat().st_size==11396
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='da8018438845bb46f70f03c84476d45b67698fb3639427ee9dfbd6b037c20f31'
previous={r['path']:r for r in json.loads((root/'results/auxiliary_tools_v1.json').read_text())}
with tarfile.open(archive) as tf:
    for member in tf:
        dest=root/member.name
        assert member.isfile() and dest.resolve().is_relative_to(root)
        if dest.exists():
            assert member.name=='tools/prepare_labels.py'
            assert hashlib.sha256(dest.read_bytes()).hexdigest()==previous[member.name]['sha256']
            backup=root/'tools/history/prepare_labels_before_audit_path_binding.py'
            backup.parent.mkdir(exist_ok=True)
            assert not backup.exists();shutil.copyfile(dest,backup)
    tf.extractall(root,filter='data')
entries=json.loads((root/'results/training_tools_v1.json').read_text())
for row in entries:
    path=root/row['path']
    assert path.stat().st_size==row['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
    if path.suffix=='.py':compile(path.read_text(),str(path),'exec')
print(json.dumps({'new_tools_and_protocol_verified':len(entries),'source_prepare_labels_preserved':True}))
PY
sinfo -o '%P|%a|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable "$stage/tools/metadata_preflight.slurm")
printf '%s\n' "$jobid"
printf '%s\n' "$jobid" > "$stage/results/metadata_preflight_job_id.txt"
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
