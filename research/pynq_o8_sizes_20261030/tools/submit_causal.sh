set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import tarfile,hashlib
root=Path('pynq_o8_sizes_20261030');a=Path('pynq_o8_sizes_20261030_causal_inputs.tar.gz');assert hashlib.sha256(a.read_bytes()).hexdigest()=='60e432de6b84a500d121e01ebf0d8b9d6d034fd18ad91a765632ffb42761028b'
assert (root/'s320/results/qualification/parity_train_4.npz').exists() and not (root/'results/probe320_causal').exists()
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(root/m.name).resolve();assert p.is_relative_to(root.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
PY
sbatch --parsable pynq_o8_sizes_20261030/tools/causal.slurm
