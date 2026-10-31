set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd /share/home/renly/projects/idcoo_research_20261026/training_coverage_20261030
../env/bin/python - <<'PY'
from pathlib import Path
import tarfile,hashlib
p=Path('loader_recovery_inputs.tar.gz');assert hashlib.sha256(p.read_bytes()).hexdigest()=='5a7cf6e564023c1d3ee74748bd98324725cec030e0b79e8492c59be3d08ddd0e'
with tarfile.open(p) as t:
 for m in t.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(t.extractfile(m).read())
PY
sbatch --parsable tools/recover_loader.slurm
