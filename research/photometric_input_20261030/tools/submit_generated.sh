set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import tarfile,hashlib
archive=Path('photometric_input_20261030_inputs_v1.tar.gz');root=Path('photometric_input_20261030')
assert not root.exists() and hashlib.sha256(archive.read_bytes()).hexdigest()=='8ad07c1ac27e5b3b9255334315edfceeca7fb9695fd9c1d0d56c26f181608a8b'
root.mkdir()
with tarfile.open(archive) as tar:
 for member in tar.getmembers():
  assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
  target=(root/member.name).resolve();assert target.is_relative_to(root.resolve()) and not target.exists()
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(member).read())
for name in ['logs','evidence','results']:(root/name).mkdir(exist_ok=True)
print('STAGED_AND_SHA_VERIFIED_BEFORE_SUBMISSION')
PY
sbatch --parsable photometric_input_20261030/tools/run.slurm
