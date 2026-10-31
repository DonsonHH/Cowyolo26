set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd /share/home/renly/projects/idcoo_research_20261026/unconfirmed_iou_20261030
../env/bin/python - <<'PY'
from pathlib import Path
import tarfile,hashlib
p=Path('baseline_diagnostic_inputs.tar.gz');assert hashlib.sha256(p.read_bytes()).hexdigest()=='be57139e4c4a450b0bbe7a268dd0b6477fed7c90b681df0cdd126b52ae175a88'
with tarfile.open(p) as t:
 for m in t.getmembers():
  assert m.isfile() and m.name=='tools/diagnose_board_baseline.py';f=Path(m.name);assert not f.exists();f.write_bytes(t.extractfile(m).read())
PY
sbatch --parsable --partition=cu --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=4G --time=00:03:00 --job-name=O8-raw-baseline-probe --output=/share/home/renly/projects/idcoo_research_20261026/unconfirmed_iou_20261030/logs/baseline-probe-%j.out --error=/share/home/renly/projects/idcoo_research_20261026/unconfirmed_iou_20261030/logs/baseline-probe-%j.err --wrap='cd /share/home/renly/projects/idcoo_research_20261026/unconfirmed_iou_20261030 && OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 ../env/bin/python -B tools/diagnose_board_baseline.py'
