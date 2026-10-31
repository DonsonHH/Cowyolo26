from pathlib import Path
import sys,subprocess,hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py';REMOTE='/share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029'
files=['protocol/evaluation_v1.json','tools/evaluate.py','tools/evaluate.slurm','tools/geometry.py',
       'input/validation_images.json','input/zone_counter.py','input/confirmation_counter.py','input/event_metrics.py']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=ROOT/'protocol/evaluation_runtime_v1.json';assert not manifest.exists();manifest.write_text(json.dumps({'files':{r:sha(ROOT/r) for r in files},'no_new_model_forwards_before_all_weight_freeze':True},indent=2)+'\n')
for relative in [*files,'protocol/evaluation_runtime_v1.json']:subprocess.run([sys.executable,str(bridge),'put',str(ROOT/relative),REMOTE+'/'+relative],check=True)
script=ROOT/'tools/submit_evaluation.sh';assert not script.exists()
script.write_text('''set -euo pipefail
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
''',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(script),'--output',str(ROOT/'evidence/evaluation_submit.txt')],check=True)
