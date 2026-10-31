set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130516,130517 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,subprocess
root=Path('/share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029')
for job in ['130516','130517']:
    state=subprocess.check_output(['sacct','-j',job,'-X','--noheader','--format=State,ExitCode','-P'],text=True).strip()
    assert state.startswith('COMPLETED|0:0'),(job,state)
assert hashlib.sha256((root/'tools/train_condition.py').read_bytes()).hexdigest()=='eafbebba1105a029d2332ab3723264beb4cd21561e4c104f1aef6714623d2450'
assert hashlib.sha256((root/'tools/train.slurm').read_bytes()).hexdigest()=='a842f55469195bfe011acd9375eb6a95bf7dd4f6037e8cc4064d575fd0e958f8'
assert hashlib.sha256((root/'protocol/formal_execution_v1.json').read_bytes()).hexdigest()=='e366018bd96a8dea0cab4d2ba0d51f3a29873c4dee6a16298152a47f80774241'
execution=json.loads((root/'protocol/formal_execution_v1.json').read_text())
assert hashlib.sha256((root/'results/preflight_grad.json').read_bytes()).hexdigest()==execution['preflight_sha256']
assert not (root/'results/training').exists()
(root/'results/training').mkdir(exist_ok=False)
print('15_FORMAL_CONDITIONS_BOUND_TO_REAL_PREFLIGHT;3_HISTORICAL_CONTROLS_PRESERVED')
PY
sbatch --parsable detector_factorial_20261029/tools/train.slurm
