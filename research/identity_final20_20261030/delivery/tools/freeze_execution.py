from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_bytes((json.dumps(v,indent=2)+'\n').encode())

assert not(ROOT/'input').exists();p=load(ROOT/'protocol/run_v1.json');prior=load(ROOT/'results/pre_pixel_review.json')
for file,digest in prior['evidence_hashes'].items():assert sha(ROOT/file)==digest
assert p['image_count']==90 and len(p['models'])==2 and p['gallery_IDs']==10
old=load(PROJECT/'pynq_identity_ncnn_20261029/protocol/encoder_v1.json')['encoder_condition'];new=load(PROJECT/'identity_domain_adapt_20261030/results/retained_candidate.json')
models=[{'name':'old_C','checkpoint':old['checkpoint'],'checkpoint_sha256':old['checkpoint_sha256'],'local_checkpoint':str(PROJECT/'identity_training_20261026/delivery/results/study/C_letterbox_trained_seed26/best_encoder.pt')},
 {'name':'new_C_domain_seed26','checkpoint':new['checkpoint_original_server'],'checkpoint_sha256':new['sha256'],'local_checkpoint':new['local_checkpoint']}]
for a,b in zip(models,p['models']):assert a['name']==b['name']and a['checkpoint_sha256']==b['checkpoint_sha256']==sha(Path(a['local_checkpoint']))
old20=next(x for x in load(PROJECT/'cows2021_identity_eval_20261030/delivery/results/evaluation/both_thresholds_frozen.json')['models']if x['model']=='C_trained_seed26')['threshold']['threshold']
new20=next(x for x in load(PROJECT/'identity_domain_adapt_20261030/delivery/results/evaluation/all6_thresholds_frozen.json')['calibration']if x['condition']=='C_domain_seed26')['threshold']['threshold']
policies={}
for model in models:
 main=next(x['threshold']for x in p['thresholds']if x['model']==model['name']and x['fold']==0);other=next(x['threshold']for x in p['thresholds']if x['model']==model['name']and x['fold']==1)
 policies[model['name']]={'primary_cal10_fold0':main,'stability_cal10_fold1':other,'legacy_MultiCam':old['threshold'],'prior_cal20':old20 if model['name']=='old_C'else new20}
target=ROOT/'tools/frozen_body_tensor.py';assert not target.exists();target.write_bytes((PROJECT/'identity_domain_ncnn_20261030/tools/frozen_body_tensor.py').read_bytes())
remote='/share/home/renly/projects/idcoo_research_20261026/identity_final20_20261030'
slurm=f'''#!/bin/bash
#SBATCH --job-name=cow-final20-id
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output={remote}/logs/evaluation-%j.out
#SBATCH --error={remote}/logs/evaluation-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1
cd {remote}
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/evaluate_final.py
''';target=ROOT/'tools/evaluation.slurm';assert not target.exists();target.write_bytes(slurm.encode())
names=['tools/evaluate_final.py','tools/acquire_final_images.py','tools/frozen_body_tensor.py','tools/evaluation.slurm','tools/collect_final.sh','tools/freeze_execution.py']
for name in names:
 if name.endswith('.py'):ast.parse((ROOT/name).read_text())
execution={'status':'MODEL_PATHS_FOUR_WORKPOINTS_CODE_AND_INFERENCE_METRICS_ARCHIVE_FROZEN_BEFORE_FIRST_FINAL_PIXEL_REQUEST','created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(ROOT/'protocol/run_v1.json'),
 'pre_pixel_review_sha256':sha(ROOT/'results/pre_pixel_review.json'),'files_sha256':{name:sha(ROOT/name)for name in names},'models':models,'threshold_policies':policies,
 'batch':12,'Torch_version':'2.8.0+cu128','Pillow_version':'11.3.0','expected_model_image_forwards':180,'expected_network_calls':16,'warmups':0,'bootstrap_seed':26030,'bootstrap_draws':2000,'bootstrap_unit':'publisher_cow_ID','tensor_anchor_indices':[0,3,30,59,60,89],
 'source_visual_indices':[0,3,30,33,59,60,75,89],'exact_primary_workpoint_fixed':'primary_cal10_fold0','appendix_workpoints_are_not_model_selection':True,'entire_project_unseen_pixels_claimed':False,'new_pixels_requested_at_freeze':0,'new_model_forwards_at_freeze':0,'whole_goal_complete':False}
save(ROOT/'protocol/execution_v1.json',execution)
save(ROOT/'results/execution_pre_pixel_gate.json',{'status':'PREVIOUS_METADATA_PROTOCOL_UNCHANGED_MODEL_HASHES_AND_ALL_CODE_AST_PASS_NO_INPUT_DIRECTORY','created_UTC':datetime.now(timezone.utc).isoformat(),'execution_sha256':sha(ROOT/'protocol/execution_v1.json'),'protocol_sha256':execution['protocol_sha256'],'same2_model_hashes':True,'workpoint_names':list(policies['old_C']),'new_model_forwards':0,'first_final_ID_pixel_request_made':False})
print(json.dumps({'status':execution['status'],'protocol_sha256':execution['protocol_sha256'],'execution_sha256':sha(ROOT/'protocol/execution_v1.json'),'primary_thresholds':{m:rows['primary_cal10_fold0']for m,rows in policies.items()},'new_pixels_requested':0,'new_model_forwards':0}))
