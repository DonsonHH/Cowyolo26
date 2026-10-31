set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,tarfile
project=Path('/share/home/renly/projects/idcoo_research_20261026');archive=project/'detector_torso_pairs_20261029_inputs.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='772c8dba5a1bd642742cc9018e039bc0d78981250d23dfcaaa3ad3cdba559c4d'
out=project/'detector_torso_pairs_20261029';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    for item in tar.getmembers():
        assert item.isfile() and not item.name.startswith('/') and '..' not in Path(item.name).parts
        target=(out/item.name).resolve();assert target.is_relative_to(out.resolve());target.parent.mkdir(parents=True,exist_ok=True)
        assert not target.exists();target.write_bytes(tar.extractfile(item).read())
for row in json.loads((out/'input/staging_manifest.json').read_text()):
    file=out/row['relative_file'];assert file.stat().st_size==row['bytes'] and hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256']
(out/'logs').mkdir(exist_ok=False)
print('STAGE_VERIFIED')
PY
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sbatch --parsable detector_torso_pairs_20261029/tools/study.slurm
