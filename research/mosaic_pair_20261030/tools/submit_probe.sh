set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
sacct -j 130628 -X --format=JobID,State,ExitCode,Elapsed -P
cd /share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030
../env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile
p=Path('regression_probe_inputs.tar.gz');assert hashlib.sha256(p.read_bytes()).hexdigest()=='c47cf69e9fad77776008c5abbf06233310c991ed2ce433bd3bbacca30437e231'
with tarfile.open(p) as t:
 for m in t.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(t.extractfile(m).read())
PY
sbatch --parsable tools/probe_regression.slurm
