set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd /share/home/renly/projects/idcoo_research_20261026/training_coverage_20261030
../env/bin/python - <<'PY'
from pathlib import Path
import tarfile,hashlib,json
a=Path('loader_inputs_v1.tar.gz');assert hashlib.sha256(a.read_bytes()).hexdigest()=='8c5426ed301166b2a753843a294a63fb544ebeec49d5ba3ff61762a3f07c0777'
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
assert json.loads(Path('results/audit/summary.json').read_text())['objects']==8888
PY
sbatch --parsable tools/loader.slurm
