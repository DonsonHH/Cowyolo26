set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd /share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030
../env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib
p=json.loads(Path('protocol/evaluation_execution_v1.json').read_text())
assert hashlib.sha256(Path('protocol/evaluation_v1.json').read_bytes()).hexdigest()==p['protocol_sha256']
for name,digest in p['files_sha256'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
assert not Path('results/evaluation').exists() and not Path('results/all_six_checkpoints_frozen.json').exists()
print('DEPENDENCY_QUEUE_ONLY;ALL_SIX_SUCCESS_AND_JOINT_WEIGHT_FREEZE_BEFORE_FORWARD')
PY
sbatch --parsable --dependency=afterok:130622 tools/evaluate.slurm
