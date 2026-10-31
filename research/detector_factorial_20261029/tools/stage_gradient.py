from pathlib import Path
import json,hashlib,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py';files=['tools/preflight_grad.py','tools/preflight_grad.slurm','protocol/gradient_gate_v1.json']
for relative in files:subprocess.run([sys.executable,str(bridge),'put',str(ROOT/relative),REMOTE+'/'+relative],check=True)
script=ROOT/'tools/submit_gradient_generated.sh';assert not script.exists()
checks='\n'.join("assert hashlib.sha256((root/"+repr(r)+").read_bytes()).hexdigest()=="+repr(sha(ROOT/r)) for r in files)
script.write_text('''set -euo pipefail
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
CHECKS
assert not (root/'results/preflight_grad.json').exists()
print('EXPLICIT_GRADIENT_PROBE_STAGED; ORIGINAL6_DISCARDED_UPDATES_PRESERVED')
PY
sbatch --parsable detector_factorial_20261029/tools/preflight_grad.slurm
'''.replace('CHECKS',checks),newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(script),'--output',str(ROOT/'evidence/gradient_submit.txt')],check=True)
