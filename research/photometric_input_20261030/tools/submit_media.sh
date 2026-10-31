set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030
../env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile
p=Path('media_inputs_v1.tar.gz');assert hashlib.sha256(p.read_bytes()).hexdigest()=='321a3e0892f2c6b16a6ceca78fba9775ad04c8d0ad053cb7a355ae50b92f5a53'
with tarfile.open(p) as t:
 for m in t.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.write_bytes(t.extractfile(m).read())
PY
sbatch --parsable --dependency=afterok:130613 tools/media.slurm
