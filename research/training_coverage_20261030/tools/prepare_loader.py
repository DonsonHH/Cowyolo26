from pathlib import Path
from datetime import datetime,timezone
import ast,json,hashlib,tarfile,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
old=PROJECT/'detector_factorial_20261029/tools/rotation_training.py';text=old.read_text(encoding='utf-8');tree=ast.parse(text)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='rotate_training_batch')
rotation='import torch\n\n'+'\n'.join(text.splitlines()[node.lineno-1:node.end_lineno])+'\n'
helper=ROOT/'input/rotation_only.py';assert not helper.exists();helper.write_text(rotation,encoding='utf-8',newline='\n')
assert ast.dump(ast.parse(rotation).body[1],include_attributes=False)==ast.dump(node,include_attributes=False)
oldp=json.loads((PROJECT/'detector_factorial_20261029/protocol/training_v4.json').read_text(encoding='utf-8'))
args={**oldp['train_kwargs_common'],'imgsz':192,'seed':26,'task':'detect','mode':'train','data':oldp['source_data_yaml']}
rows=json.loads((ROOT/'input/train_only.json').read_text(encoding='utf-8'));paths={str(Path(r['image_alias']).parent).replace('\\','/') for r in rows};assert len(paths)==1
p={'status':'FROZEN_BEFORE_REAL_TRAIN_ONLY_AUGMENTED_LOADER_EPOCH','created_host_UTC':datetime.now(timezone.utc).isoformat(),
    'loader_args':args,'train_images_path':next(iter(paths)),'seed':26,'rotation_generator_seed':710052,
    'right_angle_function_original_file_sha256':sha(old),'right_angle_function_AST_exact':True,
    'batch_size':32,'batches_expected':213,'delivered_images_expected':6809,'workers':2,'stride':32,
    'native_summary_sha256':None,'annotation_measurement':'real_transformed_training_AABB_not_native_rotated_polygon',
    'photometric_thresholds':{'Y_median_le':80,'absolute_median_contrast_le':15},
    'area_and_size_thresholds':{'shortside_lt24':24,'shortside_lt16':16,'intersection_over_min_area_ge':.1},
    'background_ring_radius_in_NN_pixels':2,'anchor_file_not_each_mosaic_component_identity':True,
    'CPU_loader_not_full_historical_training_replay':True,'worker_prefetch_may_read_extra_train_samples_not_delivered':True,
    'model_instantiation_or_forward':False,'validation_holdout_source_video_pixels_allowed':False,
    'new_training_updates':0,'whole_goal_complete':False}
save(ROOT/'protocol/loader_v1.json',p)
slurm='''#!/bin/bash
#SBATCH --job-name=training-real-loader
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=REMOTE/PHASE/logs/loader-%j.out
#SBATCH --error=REMOTE/PHASE/logs/loader-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
cd REMOTE/PHASE
../env/bin/python -B tools/audit_loader.py
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name)
f=ROOT/'tools/loader.slurm';assert not f.exists();f.write_text(slurm,encoding='utf-8',newline='\n')
files=[helper,ROOT/'input/train_only.json',ROOT/'tools/audit_loader.py',f]
save(ROOT/'protocol/loader_execution_v1.json',{'protocol_sha256':sha(ROOT/'protocol/loader_v1.json'),'files_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in files}})
staged=[helper,ROOT/'tools/audit_loader.py',f,ROOT/'protocol/loader_v1.json',ROOT/'protocol/loader_execution_v1.json']
a=ROOT/'loader_inputs_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
    for file in staged:tar.add(file,arcname=file.relative_to(ROOT).as_posix())
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
subprocess.run([sys.executable,str(bridge),'put',str(a),REMOTE+'/'+ROOT.name+'/loader_inputs_v1.tar.gz'],check=True)
cmd='''set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd REMOTE/PHASE
../env/bin/python - <<'PY'
from pathlib import Path
import tarfile,hashlib,json
a=Path('loader_inputs_v1.tar.gz');assert hashlib.sha256(a.read_bytes()).hexdigest()=='HASH'
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
assert json.loads(Path('results/audit/summary.json').read_text())['objects']==8888
PY
sbatch --parsable tools/loader.slurm
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name).replace('HASH',sha(a))
f=ROOT/'tools/submit_loader.sh';assert not f.exists();f.write_text(cmd,encoding='utf-8',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(f),'--output',str(ROOT/'evidence/loader_submission.txt')],check=True)
