"""Freeze the 13 genuinely new query forwards after deduplicating all 40 jobs."""
from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,tarfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
board=load(ROOT/'protocol/run_v1.json');jobs=load(ROOT/'results/actual_job_rows.json')
prior_root=PROJECT/'identity_trigger_pair_20261030';prior_protocol=load(prior_root/'protocol/reference_v1.json')
prior_board=load(prior_root/'protocol/run_v1.json')
prior_verified=load(prior_root/'results/reference_independent_verification.json')
assert prior_verified['actual_Torch_image_forwards']==89 and prior_verified['unique_model_input_queries']==29
assert board['source_original_protocol_sha256']==sha(prior_root/'protocol/run_v1.json')
assert board['registered_IDs']==prior_protocol['registered_IDs']
for name in['old','new']:assert board['models'][name]==prior_board['models'][name]
stage=ROOT/'reference_input';(stage/'queries').mkdir(parents=True,exist_ok=False)
prior_feature_path=prior_root/'reference_delivery/results/reference/all_features.npz'
assert sha(prior_feature_path)=='0bb641134e92f78e56a708335ac46543b4be5f2e307db78f2d08d2da2b0b8148'
(stage/'prior_all_features.npz').write_bytes(prior_feature_path.read_bytes())
for name,source in[('prior_reference_protocol.json',prior_root/'protocol/reference_v1.json'),
                    ('prior_reference_review.json',prior_root/'results/reference_independent_verification.json'),
                    ('prior_board_protocol.json',prior_root/'protocol/run_v1.json')]:
 (stage/name).write_bytes(source.read_bytes())
cached={}
for name in['old','new']:
 for i,row in enumerate(prior_protocol['gallery_images']):
  cached[(name,row['input_tensor_sha256'])]={'kind':'gallery','raw_array':name+'_gallery_raw','normalized_array':name+'_gallery_normalized','position':i}
 for i,row in enumerate([q for q in prior_protocol['queries']if q['model']==name]):
  key=(name,row['input_tensor_sha256'])
  if key not in cached:cached[key]={'kind':'query','raw_array':name+'_query_raw','normalized_array':name+'_query_normalized','position':i,'source_query_index':row['query_index']}
rows=[];assignment=[];seen={};raws={}
for job in jobs:
 key=(job['identity_model'],job['input_tensor_sha256']);photo=Path(job['photo_file']);vector=Path(job['vector_file'])
 with np.load(vector)as a:raw=a['raw'].tobytes()
 if key not in seen:
  index=len(rows);seen[key]=index;raws[key]=raw;pic=f'reference_input/queries/q{index}.png';vec=f'reference_input/queries/q{index}.npz'
  (ROOT/pic).write_bytes(photo.read_bytes());(ROOT/vec).write_bytes(vector.read_bytes())
  rows.append({'query_index':index,'model':key[0],'input_tensor_sha256':key[1],'photo_file':pic,'vector_file':vec,
                'predicted_id':job['predicted_id'],'accepted':job['accepted'],'cached_reference':cached.get(key)})
 else:assert raws[key]==raw
 assignment.append({'run':job['run'],'event':job['event'],'model':key[0],'input_tensor_sha256':key[1],'query_index':seen[key]})
with np.load(PROJECT/'pynq_identity_ncnn_20261029/board_delivery/vectors_results_v3/all_normalized_features.npz')as a:old=a['new_gallery'].copy()
with np.load(PROJECT/'identity_joint_pair_20261030/board_delivery/results/identity_qualification/all_features.npz')as a:new=a['normalized'][:30].copy()
with np.load(prior_root/'reference_input/actual_galleries.npz')as a:
 assert old.tobytes()==a['old'].tobytes()and new.tobytes()==a['new'].tobytes()
np.savez_compressed(stage/'actual_galleries.npz',old=old,new=new)
body=PROJECT/'identity_domain_ncnn_20261030/tools/frozen_body_tensor.py'
(ROOT/'tools/frozen_body_tensor.py').write_bytes(body.read_bytes())
fresh=sum(row['cached_reference']is None for row in rows);reuse=len(rows)-fresh
assert len(jobs)==40 and len(rows)==25 and fresh==13 and reuse==12
models=[{**row,'existing_encoder_bin_sha256':board['models'][row['name']]['encoder_bin_sha256']}for row in prior_protocol['models']]
protocol={'status':'FROZEN_25_MODEL_INPUTS13_NEW_FORWARDS12_REUSED_AND60_REUSED_GALLERY_VECTORS',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'source_board_protocol_sha256':sha(ROOT/'protocol/run_v1.json'),
 'models':models,'queries':rows,'actual_job_assignments':assignment,'actual_job_count':len(jobs),
 'unique_model_input_queries':len(rows),'expected_new_Torch_image_forwards':fresh,'expected_reused_query_features':reuse,
 'reused_gallery_vectors':60,'gallery_images':prior_protocol['gallery_images'],'registered_IDs':board['registered_IDs'],
 'thresholds':{'original_MultiCam':board['fixed_identity_threshold'],'secondary_Cows':board['secondary_Cows_threshold']},
 'prior_reference_protocol_sha256':sha(prior_root/'protocol/reference_v1.json'),
 'prior_reference_review_sha256':sha(prior_root/'results/reference_independent_verification.json'),
 'new_training_updates':0,'no_new_independent_data':True,'whole_goal_complete':False,
 'files':[{'file':path.relative_to(ROOT).as_posix(),'sha256':sha(path)}for path in sorted(stage.rglob('*'))if path.is_file()]}
code_names=['tools/reference_encoder.py','tools/frozen_body_tensor.py']
protocol['code_sha256']={name:sha(ROOT/name)for name in code_names}
with(ROOT/'protocol/reference_v1.json').open('x',encoding='utf-8')as f:json.dump(protocol,f,indent=2);f.write('\n')
remote='/share/home/renly/projects/idcoo_research_20261026/pynq_parent_only_trigger_20261031'
slurm=f'''#!/bin/bash
#SBATCH --job-name=cow-parent-trigger
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=5G
#SBATCH --time=00:15:00
#SBATCH --output={remote}/logs/verify-%j.out
#SBATCH --error={remote}/logs/verify-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1
cd {remote}
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/replay_tracker.py
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/reference_encoder.py
'''
script=ROOT/'tools/reference.slurm'
with script.open('xb')as f:f.write(slurm.encode())
files=[path for path in stage.rglob('*')if path.is_file()]+[ROOT/'protocol/reference_v1.json']+[ROOT/name for name in code_names]+[script]
files+=[path for path in(ROOT/'tracker_input').rglob('*')if path.is_file()]+[ROOT/'tools/replay_tracker.py']
assert len(files)==len(set(files))
for path in files:
 if path.suffix=='.py':ast.parse(path.read_text(encoding='utf-8'))
archive=ROOT/'verification_input_v1.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz')as tar:
 for path in files:tar.add(path,arcname=path.relative_to(ROOT).as_posix(),recursive=False)
meta={'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files),'new_Torch_forwards':fresh,
       'unique_model_inputs':len(rows),'reused_query_vectors':reuse,'reused_gallery_vectors':60,'new_model_forwards_by_preparation':0}
with(ROOT/'evidence/reference_input_bundle.json').open('x',encoding='utf-8')as f:json.dump(meta,f,indent=2);f.write('\n')
print(json.dumps(meta))
