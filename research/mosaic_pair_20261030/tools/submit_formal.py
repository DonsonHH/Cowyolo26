from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,subprocess,sys,ast
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
smoke=load(ROOT/'results/preflight.json');assert smoke['discarded_optimizer_updates']==4 and smoke['formal_training_updates']==0
assert smoke['status']=='BOTH_MOSAIC_ARMS_REAL_CUDA_LOSS_GRADIENT_AND_TWO_OPTIMIZER_UPDATES_PASS'
p=load(ROOT/'protocol/training_v1.json');assert smoke['protocol_sha256']==sha(ROOT/'protocol/training_v1.json')
script='''#!/bin/bash
#SBATCH --job-name=mosaic-pair-train
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=00:30:00
#SBATCH --array=0-5%3
#SBATCH --output=REMOTE/PHASE/logs/train-%A_%a.out
#SBATCH --error=REMOTE/PHASE/logs/train-%A_%a.err
set -euo pipefail
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
cd REMOTE/PHASE
../env/bin/python -B tools/train_condition.py --condition-index "$SLURM_ARRAY_TASK_ID"
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name)
file=ROOT/'tools/train.slurm';assert not file.exists();file.write_text(script,encoding='utf-8',newline='\n')
ast.parse((ROOT/'tools/train_condition.py').read_text(encoding='utf-8'))
files=[ROOT/'tools'/name for name in ['common.py','observed_trainer.py','rotation_training.py','train_condition.py','train.slurm']]
save(ROOT/'protocol/formal_execution_v1.json',{'created_host_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(ROOT/'protocol/training_v1.json'),
    'preflight_sha256':sha(ROOT/'results/preflight.json'),'files_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in files}})
staged=[ROOT/'tools/train_condition.py',file,ROOT/'protocol/formal_execution_v1.json']
a=ROOT/'formal_inputs_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
    for file in staged:tar.add(file,arcname=file.relative_to(ROOT).as_posix())
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
subprocess.run([sys.executable,str(bridge),'put',str(a),REMOTE+'/'+ROOT.name+'/formal_inputs_v1.tar.gz'],check=True)
cmd='''set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
sacct -j 130621 -X --format=JobID,State,ExitCode,Elapsed -P
cd REMOTE/PHASE
../env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,tarfile,subprocess
assert subprocess.check_output(['sacct','-j','130621','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip().startswith('COMPLETED|0:0')
assert hashlib.sha256(Path('results/preflight.json').read_bytes()).hexdigest()=='PREFLIGHT'
assert not Path('results/training').exists()
a=Path('formal_inputs_v1.tar.gz');assert hashlib.sha256(a.read_bytes()).hexdigest()=='HASH'
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
PY
sbatch --parsable tools/train.slurm
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name).replace('PREFLIGHT',sha(ROOT/'results/preflight.json')).replace('HASH',sha(a))
file=ROOT/'tools/submit_formal.sh';assert not file.exists();file.write_text(cmd,encoding='utf-8',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(file),'--output',str(ROOT/'evidence/formal_submission.txt')],check=True)
