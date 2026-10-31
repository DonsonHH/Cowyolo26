set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
sacct -j 130621 -X --format=JobID,State,ExitCode,Elapsed -P
cd /share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030
../env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,tarfile,subprocess
assert subprocess.check_output(['sacct','-j','130621','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip().startswith('COMPLETED|0:0')
assert hashlib.sha256(Path('results/preflight.json').read_bytes()).hexdigest()=='a072cc198d15f0b3a32d1e5ec6e12b479c8f3bcc41e185a8d73100cd54e8952c'
assert not Path('results/training').exists()
a=Path('formal_inputs_v1.tar.gz');assert hashlib.sha256(a.read_bytes()).hexdigest()=='844750e2f27a6ebb170cd4b16d5f79894d690fcd77b668e6a08457c0e304c574'
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
PY
sbatch --parsable tools/train.slurm
