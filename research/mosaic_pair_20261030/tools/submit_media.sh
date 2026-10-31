set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd /share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030
../env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile
p=Path('media_inputs_v1.tar.gz');assert hashlib.sha256(p.read_bytes()).hexdigest()=='d37731a74281a145941954b2cd8281eeacc365ee7594ee4b6ce72ebae25caa53'
with tarfile.open(p) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
PY
sbatch --parsable --dependency=afterok:130630 tools/media.slurm
