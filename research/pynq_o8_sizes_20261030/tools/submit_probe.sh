set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import tarfile,hashlib
root=Path('pynq_o8_sizes_20261030');a=Path('pynq_o8_sizes_20261030_probe_inputs.tar.gz');assert hashlib.sha256(a.read_bytes()).hexdigest()=='09cda2511a94cd5f7c33b271825a06fa02364f1eba96947d2f4639887bd8f4f1'
assert (root/'s320/results/qualification/parity_train_4.npz').exists() and not (root/'results/probe320').exists()
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(root/m.name).resolve();assert p.is_relative_to(root.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
PY
sbatch --parsable pynq_o8_sizes_20261030/tools/probe.slurm
