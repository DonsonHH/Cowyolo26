from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,tarfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;SOURCE=PROJECT/'identity_final20_20261030'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

source_plan=load(SOURCE/'protocol/run_v1.json');execution=load(SOURCE/'protocol/execution_v1.json');review=load(SOURCE/'results/final_review.json')
assert review['primary_Top1_C_W_U_FA']==[[22,10,2,18,3],[30,3,0,27,0]]
assert execution['protocol_sha256']==sha(SOURCE/'protocol/run_v1.json')
assert load(ROOT/'evidence/board_preflight.json')['exit_code']==0
payload=ROOT/'payload';(payload/'images').mkdir(parents=True,exist_ok=False)
hashes=load(SOURCE/'delivery/results/evaluation/input_hashes.json');audit=load(SOURCE/'results/pixel_admission.json');images=[]
for index,(row,record,digest)in enumerate(zip(source_plan['images'],audit['rows'],hashes)):
 source=SOURCE/row['local_relative_file'];assert sha(source)==record['sha256']
 name=f'images/image{index:03d}.jpg';(payload/name).write_bytes(source.read_bytes())
 images.append({'index':index,'publisher_identity':row['publisher_identity'],'purpose':row['purpose'],'is_known':row['is_known'],'capture_date':row['date'],
                'payload_image':name,'image_SHA256':record['sha256'],'input_tensor_SHA256':digest['input_tensor_sha256']})
arrays={}
for model in execution['models']:
 with np.load(SOURCE/'delivery/results/evaluation'/model['name']/'all_features.npz')as archive:
  for key in archive.files:arrays[model['name']+'_'+key]=archive[key].copy()
np.savez_compressed(payload/'CPU_reference_features.npz',**arrays)
(payload/'CPU_fixed_decisions.json').write_bytes((SOURCE/'delivery/results/evaluation/all_decisions.json').read_bytes())
for name in['board_evaluate.py','collect_results.py']:
 ast.parse((ROOT/'tools'/name).read_text());(payload/name).write_bytes((ROOT/'tools'/name).read_bytes())
legacy='/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029';new='/home/xilinx/jupyter_notebooks/cow_research_identity_domain_arm_20261030'
models=[{'name':'old_C','encoder_directory':legacy,'bin_SHA256':'8a7ac92f1d25259412c86a9f5e4f66a3c74db71128410fc03383a8f935e6815b'},
 {'name':'new_C_domain_seed26','encoder_directory':new,'bin_SHA256':'2a587d0fe293d244eb5632feb0e3665cf6091243198612b59363a6a7bb173252'}]
runtime=[{'file':m['encoder_directory']+'/encoder.ncnn.bin','sha256':m['bin_SHA256']}for m in models]
for m in models:
 runtime.extend([{'file':m['encoder_directory']+'/encoder.ncnn.param','sha256':'dd1a5af7c7f33b273508665f8332d3b48e847898981fc55989b2278022a98fe7'},
                 {'file':m['encoder_directory']+'/libcow_encoder_v2.so','sha256':'61519ebcc96c1ca396db3b9e6da96cb2c4ef1303b94a974ed491459e5c4e0731'}])
runtime.append({'file':legacy+'/ncnn_encoder_v3.py','sha256':'c7e83e2638b9cb80e4e0720b5338ac802d05b37241526226da1e482a3172027c'})
p={'status':'ALL90_INPUTS_TWO_EXISTING_NCNN_MODELS_AND480_CPU_DECISIONS_FROZEN_BEFORE_BOARD_TRANSFER_OR_FORWARD','created_UTC':datetime.now(timezone.utc).isoformat(),
 'source_CPU_protocol_SHA256':sha(SOURCE/'protocol/run_v1.json'),'source_CPU_execution_SHA256':sha(SOURCE/'protocol/execution_v1.json'),'source_CPU_final_review_SHA256':sha(SOURCE/'results/final_review.json'),
 'images':images,'registered_IDs':source_plan['roles']['registered'],'unknown_IDs':source_plan['roles']['unknown'],'models':models,'runtime_files':runtime,
 'threshold_policies':execution['threshold_policies'],'input_anchor_indices':execution['tensor_anchor_indices'],'O8_bit_sha256':'5da7a73bf52fd5153e25de5c28a40e2080c29e960d767008e0e804ec527bbfd8',
 'expected_measured_ARM_forwards':180,'expected_ARM_warmup_forwards':4,'expected_network_calls':184,'expected_retrieval_queries':120,'expected_decisions':480,
 'normalized_feature_absolute_gate':.0001,'one_minus_dot_gate':.00001,'plan_SHA256':sha(ROOT/'计划与验收.md'),'NCNN_threads':1,'new_training_updates':0,'new_PL_forwards':0,
 'full_ranking_differences_reported_not_primary_gate':True,'same_Top1_Top5_and_acceptance_required_for_pass':True,'same90_CPU_seen_images_not_new_independent_test':True,
 'new_heldout_date_pixels_opened':False,'whole_goal_complete':False,
 'payload_files':[{'file':path.relative_to(payload).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)}for path in sorted(payload.rglob('*'))if path.is_file()]}
(ROOT/'protocol').mkdir(exist_ok=False);plan=ROOT/'protocol/run_v1.json'
plan.write_bytes(json.dumps(p,indent=2).encode()+bytes([10]));(payload/'run_protocol.json').write_bytes(plan.read_bytes())
archive=ROOT/'final20_ARM_input_v1.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz')as tar:
 for path in sorted(payload.rglob('*')):
  if path.is_file():tar.add(path,arcname=path.relative_to(payload).as_posix(),recursive=False)
v={'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(p['payload_files'])+1,'protocol_sha256':sha(plan),'new_model_forwards':0};(ROOT/'evidence/input_bundle.json').write_bytes(json.dumps(v,indent=2).encode()+bytes([10]));print(json.dumps(v))
