set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
sacct -j 130617 --format=JobID,State,ExitCode,Elapsed -P
cd /share/home/renly/projects/idcoo_research_20261026/training_coverage_20261030
../env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile
p=Path('media_inputs_v1.tar.gz');assert hashlib.sha256(p.read_bytes()).hexdigest()=='1db5383cb30156d0f02ccc3d6687050344edc10b0508fd43d965ae19f169655b'
with tarfile.open(p) as t:
 for m in t.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.write_bytes(t.extractfile(m).read())
PY
sbatch --parsable --dependency=afterok:130617 tools/media.slurm
