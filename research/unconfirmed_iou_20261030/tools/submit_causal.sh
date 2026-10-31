set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd /share/home/renly/projects/idcoo_research_20261026/unconfirmed_iou_20261030
../env/bin/python - <<'PY'
from pathlib import Path
import tarfile,hashlib
p=Path('causal_inputs_v1.tar.gz');assert hashlib.sha256(p.read_bytes()).hexdigest()=='0c7f8895630da3af4abbacd50cf89b8ebeb3e038395f5189ce61b9a873117a5e'
with tarfile.open(p) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.write_bytes(tar.extractfile(m).read())
PY
sbatch --parsable --partition=cu --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=4G --time=00:03:00 --job-name=one-frame-causal --output=/share/home/renly/projects/idcoo_research_20261026/unconfirmed_iou_20261030/logs/one-frame-%j.out --error=/share/home/renly/projects/idcoo_research_20261026/unconfirmed_iou_20261030/logs/one-frame-%j.err --wrap='cd /share/home/renly/projects/idcoo_research_20261026/unconfirmed_iou_20261030 && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 ../env/bin/python -B tools/probe_one_frame.py'
