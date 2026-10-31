set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,tarfile
project=Path('/share/home/renly/projects/idcoo_research_20261026');archive=project/'lowres_baseline_20261029_inputs.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='2cb782cec13a03e70f0e44d5a26cf33b0c22f92b3242eb8db18f507ff8b9a7dd'
out=project/'lowres_baseline_20261029';out.mkdir(exist_ok=False)
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
sbatch --parsable lowres_baseline_20261029/tools/study.slurm
