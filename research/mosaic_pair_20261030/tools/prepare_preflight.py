from pathlib import Path
from datetime import datetime,timezone
import ast,json,hashlib,tarfile,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,v):assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
for name in ['protocol','input','results','logs','evidence']:(ROOT/name).mkdir(exist_ok=True)
previous=PROJECT/'detector_factorial_20261029';base=load(previous/'protocol/training_v4.json')
for name in ['common.py','observed_trainer.py','rotation_training.py']:
    dest=ROOT/'tools'/name;assert not dest.exists();dest.write_bytes((previous/'tools'/name).read_bytes())
common=ROOT/'tools/common.py';text=common.read_text(encoding='utf-8')
text=text.replace('import json,hashlib','import json,hashlib\nimport numpy as np\ndef numpy_json(value):\n    if isinstance(value,np.generic):return value.item()\n    if isinstance(value,np.ndarray):return value.tolist()\n    raise TypeError(type(value).__name__)')
text=text.replace('json.dumps(value,indent=2)','json.dumps(value,default=numpy_json,indent=2)')
common.write_text(text,encoding='utf-8',newline='\n')
conditions=[]
for seed in [26,27,28]:
    for arm,probability in [('mosaic100',1.),('mosaic050',.5)]:conditions.append({'array_index':len(conditions),'arm':arm,'mosaic':probability,'seed':seed,'imgsz':192,'name':arm+'_seed'+str(seed)})
audit=PROJECT/'training_coverage_20261030'
loader=load(audit/'results/loader_recovery_local/summary.json');assert loader['augmented_label_rows']==20292
p={'status':'FROZEN_BEFORE_ANY_NEW_MOSAIC_PAIR_TRAINING_OR_SMOKE','created_host_UTC':datetime.now(timezone.utc).isoformat(),
    'source_weights':base['source_weights'],'source_weights_sha256':base['source_weights_sha256'],'source_data_yaml':base['source_data_yaml'],
    'train_kwargs_common':base['train_kwargs_common'],'expected_initial_state_digests':base['expected_initial_state_digests'],'library':base['library'],
    'conditions':conditions,'epochs':10,'images_per_epoch':6809,'training_label_rows':8888,'validation_images':1571,'validation_label_rows':1864,
    'expected_training_batches':2130,'expected_optimizer_updates':1225,'expected_image_presentations':68090,
    'rotation':'existing_exact_RightAngleTrainer;uniform_four_turns_independent_seed710026+seed',
    'paired_factor':'mosaic_probability1.0_vs0.5_only;branch_changes_augmentation_RNG_consumption_and_component_composition',
    'not_pixel_identical_augmentations_across_arms':True,'checkpoint_rule':'Allsixlast_epoch10weights_frozen_before_source_or_Toros_evaluation;no_best_or_seed_selection',
    'source_XML_flag_kept_labels_same_both_arms':True,'source_or_Toros_images_added_to_train':False,'final_holdout_pixels_allowed':False,
    'coverage_evidence':[{'path':str(p.resolve()),'sha256':sha(p)} for p in [audit/'results/independent_verification.json',audit/'results/loader_independent_verification.json',audit/'results/publisher_annotation_flag.json']],
    'formal_training_submitted':False,'whole_goal_complete':False}
save(ROOT/'protocol/training_v1.json',p)
slurm='''#!/bin/bash
#SBATCH --job-name=mosaic-pair-preflight
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=00:08:00
#SBATCH --output=REMOTE/PHASE/logs/preflight-%j.out
#SBATCH --error=REMOTE/PHASE/logs/preflight-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
cd REMOTE/PHASE
../env/bin/python -B tools/preflight.py
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name)
f=ROOT/'tools/preflight.slurm';assert not f.exists();f.write_text(slurm,encoding='utf-8',newline='\n')
files=[ROOT/'tools'/n for n in ['common.py','observed_trainer.py','rotation_training.py','preflight.py','preflight.slurm']]
for file in files:
    if file.suffix=='.py':ast.parse(file.read_text(encoding='utf-8'))
save(ROOT/'protocol/preflight_execution_v1.json',{'protocol_sha256':sha(ROOT/'protocol/training_v1.json'),'files_sha256':{f.relative_to(ROOT).as_posix():sha(f) for f in files}})
a=ROOT/'preflight_inputs_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
    for file in [*files,ROOT/'protocol/training_v1.json',ROOT/'protocol/preflight_execution_v1.json']:tar.add(file,arcname=file.relative_to(ROOT).as_posix())
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
check=ROOT/'tools/unique_remote.sh';assert not check.exists();check.write_text('set -euo pipefail\ntest ! -e '+REMOTE+'/'+ROOT.name+'\ntest ! -e '+REMOTE+'/'+ROOT.name+'_preflight_inputs_v1.tar.gz\nsinfo -o "%P|%a|%D|%t|%N|%G"\nsqueue -u renly -o "%.18i|%.9P|%.28j|%.8T|%R"\n',encoding='utf-8',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(check),'--output',str(ROOT/'evidence/cluster_preflight.txt')],check=True)
subprocess.run([sys.executable,str(bridge),'put',str(a),REMOTE+'/'+ROOT.name+'_preflight_inputs_v1.tar.gz'],check=True)
cmd='''set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd REMOTE
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile
a=Path('PHASE_preflight_inputs_v1.tar.gz');root=Path('PHASE');assert not root.exists() and hashlib.sha256(a.read_bytes()).hexdigest()=='HASH'
root.mkdir()
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=(root/m.name).resolve();assert f.is_relative_to(root.resolve()) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
for name in ['results','logs','evidence']:(root/name).mkdir(exist_ok=True)
PY
sbatch --parsable PHASE/tools/preflight.slurm
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name).replace('HASH',sha(a))
f=ROOT/'tools/submit_preflight.sh';assert not f.exists();f.write_text(cmd,encoding='utf-8',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(f),'--output',str(ROOT/'evidence/preflight_submission.txt')],check=True)
