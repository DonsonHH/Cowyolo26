set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile
a=Path('training_coverage_20261030_audit_inputs_v1.tar.gz');root=Path('training_coverage_20261030');assert not root.exists()
assert hashlib.sha256(a.read_bytes()).hexdigest()=='5c8476b2a58427fa660d1a19009b0d52691a0f446ff0dae49dca42a25346a3ee'
root.mkdir()
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=(root/m.name).resolve();assert f.is_relative_to(root.resolve()) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
for name in ['results','logs','evidence']:(root/name).mkdir(exist_ok=True)
PY
sbatch --parsable training_coverage_20261030/tools/audit.slurm
