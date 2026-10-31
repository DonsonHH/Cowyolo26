set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030
../env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile
p=Path('source_check_inputs_v1.tar.gz');assert hashlib.sha256(p.read_bytes()).hexdigest()=='7f624e896e79d500688ffd61df2ec62dd7ad4571575a162c176bb65e717792f1'
with tarfile.open(p) as t:
 for m in t.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.write_bytes(t.extractfile(m).read())
PY
sbatch --parsable --dependency=afterok:130613 tools/source_check.slurm
