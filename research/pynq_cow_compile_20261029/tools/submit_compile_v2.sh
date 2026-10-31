set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
cd /share/home/renly/projects/idcoo_research_20261026
PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/pynq_cow_compile_20261029/dependencies:/share/home/renly/projects/idcoo_research_20261026/deployment_audit/dependencies_offline env/bin/python - <<'PY'
from pathlib import Path
import json,importlib.util,hashlib
root=Path('pynq_cow_compile_20261029');assert not (root/'results/qualification').exists()
for name in ['onnx','onnxruntime','onnxslim','torch','cv2']:assert importlib.util.find_spec(name),name
assert json.loads((root/'runtime_staging.json').read_text())['active_training_environment_modified'] is False
(root/'logs').mkdir(exist_ok=True)
print('ISOLATED_COMPILE_IMPORT_GATE_PASS;PREVIOUS_SETUP_FAILED_BEFORE_SLURM_SUBMISSION')
PY
sbatch --parsable pynq_cow_compile_20261029/tools/compile_v2.slurm
