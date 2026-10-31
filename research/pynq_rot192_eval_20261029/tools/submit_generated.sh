set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile,json
root=Path('pynq_rot192_eval_20261029');archive=Path('pynq_rot192_eval_20261029_inputs.tar.gz')
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='0fdf62cd1dd413af9471d2a4434790594b6e5a9973ec881aea0ebabc4a31a340'
assert not root.exists();root.mkdir();(root/'logs').mkdir();(root/'results').mkdir()
with tarfile.open(archive) as tar:
 for item in tar.getmembers():
  assert item.isfile() and not item.name.startswith('/') and '..' not in Path(item.name).parts
  target=(root/item.name).resolve();assert target.is_relative_to(root.resolve()) and not target.exists()
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(item).read())
print('FIXED_ROT192_QUALITY_PROTOCOL_STAGED;NO_NEW_CALIBRATION_OR_TRAINING')
PY
sbatch --parsable pynq_rot192_eval_20261029/tools/run.slurm
