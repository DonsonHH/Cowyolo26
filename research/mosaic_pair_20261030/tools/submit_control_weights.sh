set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd /share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030
../env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile
p=Path('control_weight_inputs.tar.gz');assert hashlib.sha256(p.read_bytes()).hexdigest()=='4971b8b7173fbad26c165f44276f85c6be47656ee2c6156d4b4408224071d92f'
with tarfile.open(p) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
PY
sbatch --parsable tools/control_weights.slurm
