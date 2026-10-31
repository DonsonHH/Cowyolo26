set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import tarfile,hashlib
root=Path('pynq_o8_sizes_20261030');a=Path('pynq_o8_sizes_20261030_ordered_inputs.tar.gz');assert hashlib.sha256(a.read_bytes()).hexdigest()=='bb9feef539e1c81d5f8b875d732e42f20a222ec24e1bef713fe306e9a4a58c01'
assert (root/'s320/results/qualification/parity_train_4.npz').exists() and not (root/'results/ordered_reference').exists()
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(root/m.name).resolve();assert p.is_relative_to(root.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
PY
sbatch --parsable pynq_o8_sizes_20261030/tools/ordered.slurm
