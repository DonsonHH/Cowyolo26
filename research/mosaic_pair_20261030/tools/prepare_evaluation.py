from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,subprocess,sys,ast
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
old=PROJECT/'pynq_rot192_eval_20261029';base=load(old/'protocol/eval_v2.json');port=load(PROJECT/'pynq_frontend_port_20261029/regression_v1.json')
for name,source in [('validation_images.json',old/'input/validation_images.json'),('geometry.py',old/'tools/geometry.py'),('event_metrics.py',old/'input/event_metrics.py')]:
    f=ROOT/'input'/name;assert not f.exists();f.write_bytes(source.read_bytes())
p={'status':'FROZEN_SIX_MODEL_EVALUATION_BEFORE_ANY_NEW_VIDEO_RESULT','created_host_UTC':datetime.now(timezone.utc).isoformat(),
    'training_protocol_sha256':sha(ROOT/'protocol/training_v1.json'),'videos':base['videos'],'counter_kwargs':base['counter_kwargs'],
    'tracker_config':port['tracker_config'],'port_files':port['files'],'expected_NN_input_hashes':base['expected_NN_input_hashes'],
    'validation_images':1571,'validation_references':1864,'validation_manifest_sha256':sha(ROOT/'input/validation_images.json'),
    'actual_source_image_forwards_planned':25350,'counter_paths':36,'previous_baseline_trace_count':9,'previous_baseline_regression_ticks':8202,
    'all6_last_checkpoints_must_freeze_before_forward':True,'no_model_seed_selection_on_source_counts':True,
    'new_independent_test':False,'actual_board_actions':0,'whole_goal_complete':False}
save(ROOT/'protocol/evaluation_v1.json',p)
slurm='''#!/bin/bash
#SBATCH --job-name=mosaic-pair-evaluation
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=00:15:00
#SBATCH --output=REMOTE/PHASE/logs/evaluation-%j.out
#SBATCH --error=REMOTE/PHASE/logs/evaluation-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
cd REMOTE/PHASE
../env/bin/python -B tools/evaluate.py
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name)
f=ROOT/'tools/evaluate.slurm';assert not f.exists();f.write_text(slurm,encoding='utf-8',newline='\n')
files=[ROOT/'tools/evaluate.py',f,*sorted((ROOT/'input').glob('*'))]
for file in files:
    if file.suffix=='.py':ast.parse(file.read_text(encoding='utf-8'))
save(ROOT/'protocol/evaluation_execution_v1.json',{'protocol_sha256':sha(ROOT/'protocol/evaluation_v1.json'),'files_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in files}})
a=ROOT/'evaluation_inputs_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
    for file in [*files,ROOT/'protocol/evaluation_v1.json',ROOT/'protocol/evaluation_execution_v1.json']:tar.add(file,arcname=file.relative_to(ROOT).as_posix())
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
subprocess.run([sys.executable,str(bridge),'put',str(a),REMOTE+'/'+ROOT.name+'/evaluation_inputs_v1.tar.gz'],check=True)
cmd='''set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd REMOTE/PHASE
../env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile
a=Path('evaluation_inputs_v1.tar.gz');assert hashlib.sha256(a.read_bytes()).hexdigest()=='HASH'
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
print('EVALUATION_CONFIG_STAGED;NOT_SUBMITTED;ALL_SIX_COMPLETE_REQUIRED')
PY
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name).replace('HASH',sha(a))
f=ROOT/'tools/stage_evaluation.sh';assert not f.exists();f.write_text(cmd,encoding='utf-8',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(f),'--output',str(ROOT/'evidence/evaluation_staging.txt')],check=True)
