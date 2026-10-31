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
root=Path('/share/home/renly/projects/idcoo_research_20261026');archive=root/'detector_factorial_20261029_inputs.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='f722a9e6191de66f93bbdc76e0040c5e27084f600b36f0b7637adc796721f55d'
out=root/'detector_factorial_20261029';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    for member in tar.getmembers():
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        file=(out/member.name).resolve();assert file.is_relative_to(out.resolve()) and not file.exists()
        file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(tar.extractfile(member).read())
for r in json.loads((out/'staging_manifest.json').read_text()):
    f=out/r['file'];assert f.stat().st_size==r['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==r['sha256']
(out/'results').mkdir(exist_ok=False);(out/'logs').mkdir(exist_ok=False)
print('PREFLIGHT_INPUTS_EXACT_NO_FORMAL_TRAINING_SUBMITTED')
PY
sbatch --parsable detector_factorial_20261029/tools/preflight_v2.slurm
