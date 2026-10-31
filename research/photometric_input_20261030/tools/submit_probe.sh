set -euo pipefail
sacct -j 130611 --format=JobID,State,ExitCode,Elapsed -P
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030
../env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile,subprocess
assert subprocess.check_output(['sacct','-j','130611','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip().startswith('FAILED|1:0')
p=Path('probe_v1_inputs.tar.gz');assert hashlib.sha256(p.read_bytes()).hexdigest()=='0f6fef46d8738163dc9527aa7ce5f4c78d1d3799fd56f3543e08e236da1ea110'
with tarfile.open(p) as t:
 for m in t.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.write_bytes(t.extractfile(m).read())
PY
sbatch --parsable tools/probe.slurm
