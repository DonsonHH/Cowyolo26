set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile
project=Path('/share/home/renly/projects/idcoo_research_20261026');archive=project/'factorial_lane_crop_20261029_inputs.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='f8e4b7b614e376dbd11b4263a67c3c571552a7d508311f17edde7b75c20aee4e'
root=project/'factorial_lane_crop_20261029';root.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    for member in tar.getmembers():
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        target=(root/member.name).resolve();assert target.is_relative_to(root.resolve()) and not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(member).read())
for row in json.loads((root/'staging_manifest.json').read_text()):
    file=root/row['file'];assert file.stat().st_size==row['bytes'] and hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256']
(root/'logs').mkdir(exist_ok=False)
print('ALL15_FROZEN_CHECKPOINT_CROP_INPUTS_STAGED_HASH_EXACT;NO_NEW_TRAINING')
PY
sbatch --parsable factorial_lane_crop_20261029/run.slurm
