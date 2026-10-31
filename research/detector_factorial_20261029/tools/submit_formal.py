from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,sys,subprocess
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
gate=ROOT/'evidence/preflight_gradient_result.json';smoke=json.loads(gate.read_text())
assert smoke['status']=='48_ROTATION_ORACLES_AND3_REAL_TRAINERS6_FINITE_GRADIENT_UPDATES_PASS' and smoke['formal_training_updates']==0
assert smoke['protocol_sha256']==sha(ROOT/'protocol/training_v4.json') and len(smoke['geometry_oracles'])==48
assert all(len(r['gradient_audits'])==2 and all(q['finite_gradient_tensors']>0 and q['nonzero_gradient_tensors']>0 for q in r['gradient_audits']) for r in smoke['real_trainer_runs'])
p={'status':'FROZEN_BEFORE_FORMAL_15_RUN_ARRAY_SUBMISSION','created_UTC':datetime.now(timezone.utc).isoformat(),
   'base_protocol_sha256':sha(ROOT/'protocol/training_v4.json'),'preflight_sha256':sha(gate),
   'preflight_gradient_script_sha256':sha(ROOT/'tools/preflight_grad.py'),'training_script_sha256':sha(ROOT/'tools/train_condition.py'),
   'slurm_script_sha256':sha(ROOT/'tools/train.slurm'),'new_conditions':15,'max_concurrent_jobs':3,
   'historical_controls':3,'epochs':10,'batches_each_run':2130,'expected_optimizer_updates_each_run':1225,
   'checkpoint':'fixedlast_epoch10','all_weights_frozen_before_source_Toros_inference':True,'whole_goal_complete':False}
file=ROOT/'protocol/formal_execution_v1.json';assert not file.exists();file.write_text(json.dumps(p,indent=2)+'\n')
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py';files=['tools/train_condition.py','tools/train.slurm','protocol/formal_execution_v1.json']
for relative in files:subprocess.run([sys.executable,str(bridge),'put',str(ROOT/relative),REMOTE+'/'+relative],check=True)
script=ROOT/'tools/submit_formal_generated.sh';assert not script.exists()
checks='\n'.join("assert hashlib.sha256((root/"+repr(r)+").read_bytes()).hexdigest()=="+repr(sha(ROOT/r)) for r in files)
text='''set -euo pipefail
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
CHECKS
execution=json.loads((root/'protocol/formal_execution_v1.json').read_text())
assert hashlib.sha256((root/'results/preflight_grad.json').read_bytes()).hexdigest()==execution['preflight_sha256']
assert not (root/'results/training').exists()
(root/'results/training').mkdir(exist_ok=False)
print('15_FORMAL_CONDITIONS_BOUND_TO_REAL_PREFLIGHT;3_HISTORICAL_CONTROLS_PRESERVED')
PY
sbatch --parsable detector_factorial_20261029/tools/train.slurm
'''.replace('CHECKS',checks)
script.write_text(text,newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(script),'--output',str(ROOT/'evidence/formal_submit.txt')],check=True)
