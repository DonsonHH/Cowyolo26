from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,tarfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_bytes(json.dumps(v,indent=2).encode()+bytes([10]))

p=load(ROOT/'protocol/run_v1.json');jobs=load(ROOT/'results/actual_job_rows.json');stage=ROOT/'reference_input';(stage/'queries').mkdir(parents=True,exist_ok=False)
rows=[];assignment=[];keys={};seen_raw={}
for job in jobs:
 key=(job['identity_model'],job['input_tensor_sha256']);photo=Path(job['photo_file']);vector=Path(job['vector_file'])
 with np.load(vector)as a:rawbytes=a['raw'].tobytes()
 if key not in keys:
  index=len(rows);keys[key]=index;seen_raw[key]=rawbytes;pic='reference_input/queries/q'+str(index)+'.png';vec='reference_input/queries/q'+str(index)+'.npz';(ROOT/pic).write_bytes(photo.read_bytes());(ROOT/vec).write_bytes(vector.read_bytes())
  rows.append({'query_index':index,'model':job['identity_model'],'input_tensor_sha256':key[1],'photo_file':pic,'vector_file':vec,'predicted_id':job['predicted_id'],'accepted':job['accepted']})
 else:assert seen_raw[key]==rawbytes
 assignment.append({'run':job['run'],'input_tensor_sha256':key[1],'event':job['event'],'model':key[0],'query_index':keys[key]})
with np.load(PROJECT/'pynq_identity_ncnn_20261029/board_delivery/vectors_results_v3/all_normalized_features.npz')as a:old=a['new_gallery'].copy()
with np.load(PROJECT/'identity_joint_pair_20261030/board_delivery/results/identity_qualification/all_features.npz')as a:new=a['normalized'][:30].copy()
np.savez_compressed(stage/'actual_galleries.npz',old=old,new=new)
orig=load(PROJECT/'pynq_identity_ncnn_20261029/input/images.json')['new_gallery'];reference_images=load(PROJECT/'identity_joint_pair_20261030/protocol/cpu_reference_v1.json')['images'][:30]
gallery=[{'identity':r['identity'],'server_image':r['path'],'sha256':r['sha256'],'input_tensor_sha256':q['input_tensor_sha256']}for r,q in zip(orig,reference_images)]
oldmodel=load(PROJECT/'pynq_identity_ncnn_20261029/protocol/encoder_v1.json')['encoder_condition'];newmodel=load(PROJECT/'identity_domain_adapt_20261030/results/retained_candidate.json')
models=[{'name':'old','checkpoint':oldmodel['checkpoint'],'checkpoint_sha256':oldmodel['checkpoint_sha256']},{'name':'new','checkpoint':newmodel['checkpoint_original_server'],'checkpoint_sha256':newmodel['sha256']}]
source=PROJECT/'identity_domain_ncnn_20261030/tools/frozen_body_tensor.py';target=ROOT/'tools/frozen_body_tensor.py';assert not target.exists();target.write_bytes(source.read_bytes())
protocol={'status':'FROZEN_UNIQUE_MODEL_INPUT_REFERENCE_BEFORE_ANY_NEW_TORCH_FORWARD','created_UTC':datetime.now(timezone.utc).isoformat(),'models':models,'queries':rows,'actual_job_assignments':assignment,'actual_job_count':len(jobs),'unique_model_input_queries':len(rows),'expected_Torch_image_forwards':len(rows)+60,
 'gallery_images':gallery,'registered_IDs':p['registered_IDs'],'thresholds':{'original_MultiCam':p['fixed_identity_threshold'],'secondary_Cows':p['secondary_Cows_threshold']},
 'new_training_updates':0,'source_board_protocol_SHA256':sha(ROOT/'protocol/run_v1.json'),'same_source_no_new_ID_pixels':True,'files':[{'file':f.relative_to(ROOT).as_posix(),'sha256':sha(f)}for f in sorted(stage.rglob('*'))if f.is_file()],'whole_goal_complete':False}
save(ROOT/'protocol/reference_v1.json',protocol)
remote='/share/home/renly/projects/idcoo_research_20261026/identity_trigger_pair_20261030'
slurm=f'''#!/bin/bash
#SBATCH --job-name=cow-trigger-verify
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=5G
#SBATCH --time=00:15:00
#SBATCH --output={remote}/logs/verify-%j.out
#SBATCH --error={remote}/logs/verify-%j.err
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd {remote}
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/replay_tracker.py
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/reference_encoder.py
'''
script=ROOT/'tools/reference.slurm';assert not script.exists();script.write_bytes(slurm.encode())
names=['tools/reference_encoder.py','tools/frozen_body_tensor.py','tools/reference.slurm']
save(ROOT/'protocol/reference_execution_v1.json',{'protocol_sha256':sha(ROOT/'protocol/reference_v1.json'),'code_sha256':{name:sha(ROOT/name)for name in names}})
files=[f for f in stage.rglob('*')if f.is_file()]+[ROOT/'protocol/reference_v1.json',ROOT/'protocol/reference_execution_v1.json']+[ROOT/name for name in names]+[f for f in(ROOT/'tracker_input').rglob('*')if f.is_file()]+[ROOT/'tools/replay_tracker.py']
a=ROOT/'verification_input_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz')as tar:
 for f in files:tar.add(f,arcname=f.relative_to(ROOT).as_posix(),recursive=False)
v={'bytes':a.stat().st_size,'sha256':sha(a),'members':len(files),'unique_query_inputs':len(rows),'actual_query_jobs':len(jobs),'planned_Torch_forwards':len(rows)+60,'new_model_forwards':0};save(ROOT/'evidence/verification_input_bundle.json',v);print(json.dumps(v))
