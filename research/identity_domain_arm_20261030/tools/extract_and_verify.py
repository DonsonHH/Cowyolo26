"""Independently recompute the full saved ARM experiment; no model inference."""
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import argparse,hashlib,importlib.util,json,tarfile
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

parser=argparse.ArgumentParser();parser.add_argument('--resume-verified-extraction',action='store_true');args=parser.parse_args()
transfer=load(ROOT/'evidence/result_transfer.json');archive=ROOT/'new_identity_ARM_delivery_v1.tar.xz'
assert archive.stat().st_size==transfer['bytes']and sha(archive)==transfer['sha256']
out=ROOT/'delivery'
if out.exists():assert args.resume_verified_extraction and(out/'result_manifest.json').is_file()
else:out.mkdir(exist_ok=False)
with tarfile.open(archive)as tar:
 members=tar.getmembers();assert len(members)==transfer['members']
 for member in members:
  name=PurePosixPath(member.name);assert member.isfile()and not name.is_absolute()and'..'not in name.parts
  target=(out/member.name).resolve();assert target.is_relative_to(out.resolve());data=tar.extractfile(member).read()
  if target.exists():assert args.resume_verified_extraction and target.read_bytes()==data
  else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
manifest=load(out/'result_manifest.json');assert len(manifest)==transfer['manifest_files']
for row in manifest:
 p=out/row['file'];assert p.stat().st_size==row['bytes']and sha(p)==row['sha256']
assert sha(out/'run_protocol.json')==sha(ROOT/'protocol/run_v1.json')
plan=load(out/'run_protocol.json');state=load(out/'results/record.json');done=load(out/'results/terminal.json')
assert state['status']==done['status']=='ALL97_NEW_ENCODER_ARM_VECTORS_INPUT_HASHES_AND120_RETENTION_DECISIONS_PASS'
assert done['record_sha256']==sha(out/'results/record.json')and done['model_forwards']==state['model_forwards']==97
assert len(state['warmups'])==2 and len(state['rows'])==97 and state['new_PL_forwards']==0 and not state['PL_programming']and not state['Torch_imported']
for file in['board_test.py','collect_results.py']:assert sha(out/file)==sha(ROOT/'payload'/file)
binding=load(out/'collection_execution_v2.json');assert binding==load(ROOT/'protocol/collection_execution_v2.json')
assert sha(out/'collect_results_v2.py')==binding['new_collection_sha256']
assert hashlib.sha256((ROOT/'tools/collect_results_v2.py').read_text().encode()).hexdigest()==binding['new_collection_sha256']
assert sha(out/'collect_results.py')==binding['original_collection_sha256']and binding['new_model_forwards']==0
assert "AttributeError: 'str' object has no attribute 'read_bytes'"in(out/'collection.log').read_text()
source=PROJECT/'identity_domain_ncnn_20261030';source_plan=load(source/'protocol/run_v1.json')
with np.load(source/'delivery/results/export/all_features.npz')as archive:ref={key:archive[key].copy()for key in archive.files}
with np.load(ROOT/'payload/reference_features.npz')as archive:subset={key:archive[key].copy()for key in archive.files}
indices=[row['source_global630_index']for row in plan['images']]
for key in subset:assert np.array_equal(ref[key][indices],subset[key])
with np.load(out/'results/all_actual_features.npz')as archive:values={key:archive[key].copy()for key in archive.files}
assert set(values)=={'raw','normalized'}and all(a.shape==(97,576)and np.isfinite(a).all()for a in values.values())
norm=values['raw'].astype(float);norm=norm/np.sqrt(np.sum(norm**2,axis=1))[:,None]
assert np.max(np.abs(norm-values['normalized']))<1e-7
pre=load(out/'results/preprocessing_gate.json');assert len(pre['rows'])==97 and pre['model_forwards']==0
spec=importlib.util.spec_from_file_location('fixed_body_for_audit',source/'tools/frozen_body_tensor.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
errors=[];ncnn_errors=[]
for index,(row,actual,pr)in enumerate(zip(plan['images'],state['rows'],pre['rows'])):
 global_index=row['source_global630_index'];image=source_plan['images'][global_index]
 path=PROJECT/'cows2021_identity_eval_20261030'/image['local_relative_file']if image['group']!='retention'else PROJECT/'identity_training_20261026/delivery'/image['relative_path']
 assert sha(path)==row['image_SHA256']
 with Image.open(path)as photo:x=module.body_tensor(photo)
 digest=hashlib.sha256(x.tobytes()).hexdigest();assert digest==row['input_tensor_sha256']==actual['input_tensor_sha256']==pr['input_tensor_sha256']
 assert hashlib.sha256(values['raw'][index].tobytes()).hexdigest()==actual['actual_ARM_raw_sha256']
 error=float(np.max(np.abs(values['normalized'][index]-subset['Torch_normalized'][index])))
 cosine=1-float(values['normalized'][index].astype(float)@subset['Torch_normalized'][index].astype(float))
 assert error==actual['normalized_Torch_error']and abs(cosine-actual['one_minus_cosine'])<2e-15
 assert error<=plan['normalized_feature_max_absolute_error']and cosine<=plan['max_1_minus_cosine_error']
 errors.append(error);ncnn_errors.append(float(np.max(np.abs(values['normalized'][index]-subset['NCNN_normalized'][index]))))
 if index in plan['input_anchor_test_indices']:
  with np.load(out/'results/input_anchors'/('test'+str(index)+'.npz'))as anchor:
   assert anchor['input'].tobytes()==x.tobytes()and np.array_equal(anchor['raw'],values['raw'][index])and np.array_equal(anchor['normalized'],values['normalized'][index])
gi=[r['test_index']for r in plan['images']if r['dataset']=='MultiCam2023'and r['purpose']=='gallery']
qi=[r['test_index']for r in plan['images']if r['dataset']=='MultiCam2023'and r['purpose']!='gallery']
labels=sorted({plan['images'][j]['identity']for j in gi});assert len(gi)==30 and len(qi)==60 and len(labels)==6
scores={backend:{index:{identity:max(float(np.dot(features[index].astype(float),features[j].astype(float)))for j in gi if plan['images'][j]['identity']==identity)for identity in labels}for index in qi}for backend,features in[('Torch',subset['Torch_normalized']),('ARM',values['normalized'])]}
retrieval=load(out/'results/retrieval_parity.json');assert len(retrieval)==120;outcomes={};checked=0
for policy,tau in[('original_MultiCam',plan['original_MultiCam_threshold']),('new_Cows_calibrated',plan['new_Cows_threshold'])]:
 result={'known_queries':0,'unknown_queries':0,'known_Top1':0,'C':0,'W':0,'U':0,'unknown_FA':0}
 for index in qi:
  decisions={backend:(sorted(row[index],key=lambda label:(-row[index][label],label))[0])for backend,row in scores.items()}
  a,b=decisions['Torch'],decisions['ARM'];accept=scores['ARM'][index][b]>=tau
  assert a==b and accept==(scores['Torch'][index][a]>=tau)
  original=next(r for r in retrieval if r['policy']==policy and r['test_index']==index)
  assert original['predicted_ID']==b and original['reference_predicted_ID']==a and original['accepted']==accept and original['reference_accepted']==accept
  diff=max(abs(scores['Torch'][index][label]-scores['ARM'][index][label])for label in labels)
  assert abs(diff-original['maximum_cosine_difference'])<2e-15
  row=plan['images'][index]
  if row['is_known']:
   result['known_queries']+=1;result['known_Top1']+=int(b==row['identity']);result['C'if accept and b==row['identity']else'W'if accept else'U']+=1
  else:result['unknown_queries']+=1;result['unknown_FA']+=int(accept)
  checked+=1
 outcomes[policy]=result
assert checked==120
timing=np.array([row['network_ms']for row in state['rows']]);assert abs(float(timing.mean())-state['mean_network_ms'])<1e-10 and abs(float(np.quantile(timing,.95))-state['P95_network_ms'])<1e-10
final=load(out/'final_board_state.json');assert not final['experiment_proc_exists']and final['lock_available']and final['local_services']=={'22':True,'9090':True}
assert final['PL_sha256']==plan['O8_bit_sha256']and final['default_old_encoder_bin_sha256']==plan['default_old_encoder_bin_sha256']
result={'status':'FULL97_ARM_INPUTS_RAW_FEATURES9_ANCHORS120_DECISIONS_AND_TERMINAL_STATE_INDEPENDENTLY_RECOMPUTED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'actual_ARM_measured_forwards':97,'actual_ARM_warmups':2,'new_PL_forwards':0,'independently_recomputed_source_and_tensor_hashes':97,'full_input_anchors':9,
 'independently_recomputed_decisions':120,'independently_recomputed_ID_scores':720,'retention_outcomes':outcomes,
 'maximum_normalized_ARM_vs_Torch_error':max(errors),'maximum_normalized_ARM_vs_NCNN_error':max(ncnn_errors),'mean_network_ms':float(timing.mean()),'P95_network_ms':float(np.quantile(timing,.95)),
 'mean_JPEG_decode_preprocess_ms':float(np.mean([row['JPEG_decode_and_preprocess_ms']for row in pre['rows']])),'P95_JPEG_decode_preprocess_ms':float(np.quantile([row['JPEG_decode_and_preprocess_ms']for row in pre['rows']],.95)),
 'original_archive_bytes':transfer['bytes'],'manifest_files':len(manifest),'independent_full_Cows_accuracy':False,'concurrent_detector_5FPS_test':False,'verification_additional_model_forwards':0,'whole_goal_complete':False}
(ROOT/'results').mkdir(exist_ok=True);target=ROOT/'results/independent_verification.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
