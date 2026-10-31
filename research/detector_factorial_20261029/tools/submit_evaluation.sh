set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib
root=Path('detector_factorial_20261029')
for relative,digest in json.loads((root/'protocol/evaluation_runtime_v1.json').read_text())['files'].items():assert hashlib.sha256((root/relative).read_bytes()).hexdigest()==digest
assert not (root/'results/evaluation').exists()
print('ALL15_MODEL_EVALUATION_STAGED;AFTER_OK_RECOVERY_DEPENDENCY_REQUIRES_WEIGHT_FREEZE')
PY
sbatch --parsable --dependency=afterok:130542 detector_factorial_20261029/tools/evaluate.slurm
