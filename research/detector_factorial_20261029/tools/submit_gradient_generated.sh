set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,subprocess
root=Path('/share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029')
state=subprocess.check_output(['sacct','-j','130516','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip()
assert state.startswith('COMPLETED|0:0'),state
assert json.loads((root/'results/preflight.json').read_text())['formal_training_updates']==0
assert hashlib.sha256((root/'tools/preflight_grad.py').read_bytes()).hexdigest()=='33c3ae0b036522778df01a797bfb6be91ac078dc0ea54922942a9d0f54ee1747'
assert hashlib.sha256((root/'tools/preflight_grad.slurm').read_bytes()).hexdigest()=='fefab62f56a2acbda290e00cbdc60af17114da531fe55979f72faab8abd65226'
assert hashlib.sha256((root/'protocol/gradient_gate_v1.json').read_bytes()).hexdigest()=='1ca31f447a62109e9ea7fc9a461c4a837debc1b6c96a181d86823e4a320b7d03'
assert not (root/'results/preflight_grad.json').exists()
print('EXPLICIT_GRADIENT_PROBE_STAGED; ORIGINAL6_DISCARDED_UPDATES_PRESERVED')
PY
sbatch --parsable detector_factorial_20261029/tools/preflight_grad.slurm
