from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,tarfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

source=PROJECT/'identity_domain_ncnn_20261030';p=load(source/'protocol/run_v1.json');export=source/'delivery/results/export'
summary=load(export/'summary.json');assert summary['development_decision_differences']==0
indices=[540+index for index in range(90)]+[0,60,120,180,300,420,539]
source_numeric=load(export/'input_and_numeric_rows.json');legacygroups=load(PROJECT/'pynq_identity_ncnn_20261029/input/images.json')
old_image_map={row['sha256']:f"/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/images/{group}_{index:03d}.jpg"for group in['old_gallery','labelled_query']for index,row in enumerate(legacygroups[group])}
(ROOT/'payload/images').mkdir(parents=True,exist_ok=False);records=[]
for test_index,index in enumerate(indices):
 row=p['images'][index];image_hash=row['image_SHA256'];new={'test_index':test_index,'source_global630_index':index,'identity':row['identity'],'purpose':row['purpose'],
  'is_known':row['is_known'],'dataset':'MultiCam2023'if index>=540 else'Cows2021','image_SHA256':image_hash,'input_tensor_sha256':source_numeric[index]['input_tensor_sha256']}
 if index>=540:
  assert image_hash in old_image_map;new['existing_board_image']=old_image_map[image_hash]
 else:
  local=PROJECT/'cows2021_identity_eval_20261030'/row['local_relative_file'];assert sha(local)==image_hash
  name='images/Cows_index'+str(index)+'.jpg';shutil.copyfile(local,ROOT/'payload'/name);new['payload_image']=name
 records.append(new)
for name in['encoder.ncnn.param','encoder.ncnn.bin']:shutil.copyfile(export/name,ROOT/'payload'/name)
with np.load(export/'all_features.npz')as arrays:
 np.savez_compressed(ROOT/'payload/reference_features.npz',**{key:arrays[key][indices].copy()for key in arrays.files})
plan={'status':'FROZEN_BEFORE_NEW_IDENTITY_WEIGHT_BOARD_TRANSFER_OR_ARM_FORWARD','created_UTC':datetime.now(timezone.utc).isoformat(),
      'source_checkpoint_sha256':p['checkpoint_sha256'],'NCNN_bin_sha256':summary['NCNN_bin_sha256'],'NCNN_param_sha256':summary['NCNN_param_sha256'],
      'library_sha256':'61519ebcc96c1ca396db3b9e6da96cb2c4ef1303b94a974ed491459e5c4e0731',
      'body_module_sha256':p['body_module_sha256'],'default_old_encoder_bin_sha256':'8a7ac92f1d25259412c86a9f5e4f66a3c74db71128410fc03383a8f935e6815b',
      'O8_bit_sha256':'5da7a73bf52fd5153e25de5c28a40e2080c29e960d767008e0e804ec527bbfd8',
      'images':records,'input_anchor_test_indices':[0,29,89,90,91,92,93,94,95],
      'expected_measured_ARM_forwards':97,'expected_warmups':2,'expected_retention_retrieval_decisions':120,
      'normalized_feature_max_absolute_error':.0001,'max_1_minus_cosine_error':.00001,
      'new_Cows_threshold':p['new_Cows_threshold'],'original_MultiCam_threshold':p['original_MultiCam_threshold'],
      'plan_sha256':sha(ROOT/'计划与验收.md'),'future20_ID_pixels_opened':False,'new_training_updates':0,'new_PL_forwards':0,'whole_goal_complete':False}
for name in['board_test.py','collect_results.py']:shutil.copyfile(ROOT/'tools'/name,ROOT/'payload'/name)
plan['payload_files']=[{'file':path.relative_to(ROOT/'payload').as_posix(),'sha256':sha(path),'bytes':path.stat().st_size}for path in(ROOT/'payload').rglob('*')if path.is_file()]
(ROOT/'protocol').mkdir(exist_ok=False);(ROOT/'evidence').mkdir(exist_ok=False);(ROOT/'protocol/run_v1.json').write_text(json.dumps(plan,indent=2)+'\n');(ROOT/'payload/run_protocol.json').write_text(json.dumps(plan,indent=2)+'\n')
archive=ROOT/'new_identity_board_input_v1.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz')as tar:
 for path in(ROOT/'payload').rglob('*'):
  if path.is_file():tar.add(path,arcname=path.relative_to(ROOT/'payload').as_posix(),recursive=False)
record={'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(plan['payload_files'])+1,'protocol_sha256':sha(ROOT/'protocol/run_v1.json'),'new_model_forwards':0}
(ROOT/'evidence/input_bundle.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
