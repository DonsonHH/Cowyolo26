from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
from collections import defaultdict
import hashlib,importlib.util,json,tarfile
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT.parent/'identity_final20_20261030'
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_bytes(json.dumps(v,indent=2).encode()+bytes([10]))

t=load(ROOT/'evidence/result_transfer.json');archive=ROOT/'final20_ARM_delivery_v1.tar.xz'
assert archive.stat().st_size==t['bytes']and sha(archive)==t['sha256']
out=ROOT/'delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive)as tar:
 members=tar.getmembers();assert len(members)==t['members']
 for m in members:
  rel=PurePosixPath(m.name);assert m.isfile()and not rel.is_absolute()and'..'not in rel.parts
  p=(out/m.name).resolve();assert p.is_relative_to(out.resolve())and not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
manifest=load(out/'result_manifest.json');assert len(manifest)==t['manifest_files']
for r in manifest:assert sha(out/r['file'])==r['sha256']and(out/r['file']).stat().st_size==r['bytes']
assert sha(out/'run_protocol.json')==sha(ROOT/'protocol/run_v1.json')
for name in['board_evaluate.py','collect_results.py']:assert sha(out/name)==sha(ROOT/'payload'/name)
plan=load(out/'run_protocol.json');state=load(out/'results/record.json');terminal=load(out/'results/terminal.json')
assert terminal['record_sha256']==sha(out/'results/record.json')and state['status']==terminal['status']
assert state['measured_forwards']==terminal['measured_forwards']==180 and state['warmup_forwards']==terminal['warmup_forwards']==4 and state['attempted_network_calls']==184
assert state['new_PL_forwards']==0 and state['PL_programming']is False and state['Torch_imported']is False
assert state['PL_after_SHA256']==plan['O8_bit_sha256']
final=load(out/'final_board_state.json');assert not final['experiment_proc_exists']and final['all_runtime_hashes_match']and final['shared_lock_available']and all(final['local_services'].values())
sourceplan=load(SOURCE/'protocol/run_v1.json');execution=load(SOURCE/'protocol/execution_v1.json')
assert sha(SOURCE/'protocol/run_v1.json')==plan['source_CPU_protocol_SHA256']and sha(SOURCE/'protocol/execution_v1.json')==plan['source_CPU_execution_SHA256']
assert plan['threshold_policies']==execution['threshold_policies']
spec=importlib.util.spec_from_file_location('verify_fixed_body',SOURCE/'tools/frozen_body_tensor.py');body=importlib.util.module_from_spec(spec);spec.loader.exec_module(body)
pre=load(out/'results/preprocessing_gate.json');assert pre['model_forwards']==0 and len(pre['rows'])==90
for index,(row,cpu,pr)in enumerate(zip(plan['images'],sourceplan['images'],pre['rows'])):
 jpeg=SOURCE/cpu['local_relative_file'];assert sha(jpeg)==row['image_SHA256']==sha(ROOT/'payload'/row['payload_image'])
 with Image.open(jpeg)as image:image.load();x=body.body_tensor(image)
 digest=hashlib.sha256(x.tobytes()).hexdigest();assert digest==row['input_tensor_SHA256']==pr['input_tensor_sha256']and pr['index']==index
 if index in plan['input_anchor_indices']:
  with np.load(out/'results/input_anchors'/('index'+str(index)+'.npz'))as a:assert a['input'].tobytes()==x.tobytes()
CPU=load(SOURCE/'delivery/results/evaluation/all_decisions.json');CPUranks={}
features={};allerrs=[];timings={}
for model in plan['models']:
 name=model['name'];m=state['models'][name];assert m['measured_forwards']==90 and len(m['rows'])==90 and len(m['warmups'])==2
 assert load(out/'results'/name/'record.json')==m
 with np.load(out/'results'/name/'actual_features.npz')as a:raw=a['raw'].copy();f=a['normalized'].copy()
 with np.load(SOURCE/'delivery/results/evaluation'/name/'all_features.npz')as a:ref=a['normalized'].copy();cpu_raw=a['raw'].copy()
 with np.load(ROOT/'payload/CPU_reference_features.npz')as a:assert a[name+'_normalized'].tobytes()==ref.tobytes()and a[name+'_raw'].tobytes()==cpu_raw.tobytes()
 assert raw.shape==f.shape==(90,576)and np.isfinite(raw).all()and np.isfinite(f).all()
 normalized=raw.astype(float)/np.sqrt(np.sum(raw.astype(float)**2,axis=1))[:,None];assert np.max(np.abs(normalized-f))<1e-7
 errors=[]
 for index,row in enumerate(m['rows']):
  assert row['index']==index and row['input_tensor_sha256']==pre['rows'][index]['input_tensor_sha256']
  assert hashlib.sha256(raw[index].tobytes()).hexdigest()==row['raw_feature_sha256']
  delta=float(np.max(np.abs(f[index]-ref[index])));dot=1-float(f[index].astype(float)@ref[index].astype(float));passed=delta<=.0001 and dot<=.00001
  assert delta==row['normalized_Torch_error']and abs(dot-row['one_minus_dot'])<2e-15 and passed==row['numeric_pass'];errors.append(delta)
 tms=np.array([row['network_ms']for row in m['rows']]);assert abs(float(tms.mean())-m['network_mean_ms'])<1e-10 and abs(float(np.quantile(tms,.95))-m['network_P95_ms'])<1e-10
 assert max(errors)==m['maximum_normalized_feature_error']and sum(not row['numeric_pass']for row in m['rows'])==m['numeric_failed_images']
 timings[name]={'images':90,'warmups':[r['network_ms']for r in m['warmups']],'network_mean_ms':float(tms.mean()),'network_P95_ms':float(np.quantile(tms,.95)),'network_min_ms':float(tms.min()),'network_max_ms':float(tms.max()),'maximum_normalized_ARM_CPU_error':max(errors)}
 features[name]=f;allerrs.extend(errors)
gi=[r['index']for r in plan['images']if r['purpose']=='gallery'];qi=[r['index']for r in plan['images']if r['purpose']!='gallery'];labels=sorted(plan['registered_IDs'])
retrieval=load(out/'results/all_retrieval.json');decisions=load(out/'results/all_decisions.json');outcomes=load(out/'results/all_outcomes.json')
assert len(retrieval)==120 and len(decisions)==480 and len(outcomes)==8
idcells=0;top1changes=top5changes=rankingchanges=decisionchanges=0;derivedout=[]
for name,f in features.items():
 for index in qi:
  r=next(r for r in retrieval if r['model']==name and r['source_index']==index)
  values={ID:max(float(np.dot(f[index].astype(float),f[j].astype(float)))for j in gi if plan['images'][j]['publisher_identity']==ID)for ID in labels}
  order=sorted(labels,key=lambda ID:(-values[ID],ID));cpu=next(r for r in CPU if r['model']==name and r['policy']=='primary_cal10_fold0'and r['source_index']==index)
  cpuorder=sorted(labels,key=lambda ID:(-cpu['all_ID_scores'][ID],ID));diff=max(abs(values[ID]-cpu['all_ID_scores'][ID])for ID in labels)
  assert all(abs(values[ID]-r['all_ID_scores'][ID])<1e-12 for ID in labels)
  assert r['predicted_id']==order[0]and r['top5_IDs']==order[:5]and r['CPU_predicted_id']==cpu['predicted_id']and r['CPU_top5_IDs']==cpu['top5_IDs']
  assert r['same_Top1']==(order[0]==cpu['predicted_id'])and r['same_Top5_order']==(order[:5]==cpu['top5_IDs'])and r['same_full_ranking']==(order==cpuorder)
  assert abs(diff-r['maximum_registered_score_difference'])<1e-12;idcells+=10;top1changes+=not r['same_Top1'];top5changes+=not r['same_Top5_order'];rankingchanges+=not r['same_full_ranking']
 for policy,tau in plan['threshold_policies'][name].items():
  rr=[r for r in decisions if r['model']==name and r['policy']==policy];assert len(rr)==60
  for r in rr:
   cp=next(c for c in CPU if c['model']==name and c['policy']==policy and c['source_index']==r['source_index']);pred=next(x for x in retrieval if x['model']==name and x['source_index']==r['source_index'])
   value=pred['all_ID_scores'][pred['predicted_id']];assert r['threshold']==tau and r['score']==value and r['accepted']==(value>=tau)and r['predicted_id']==pred['predicted_id']
   assert r['CPU_accepted']==cp['accepted']and r['CPU_predicted_id']==cp['predicted_id'];same=r['predicted_id']==cp['predicted_id']and r['accepted']==cp['accepted'];assert same==r['same_CPU_Top1_and_accept'];decisionchanges+=not same
  known=[r for r in rr if r['is_known']];unknown=[r for r in rr if not r['is_known']]
  summary={'model':name,'policy':policy,'known_queries':30,'unknown_queries':30,'known_Top1':sum(r['identity']==r['predicted_id']for r in known),'known_Top5':sum(r['identity']in r['top5_IDs']for r in known),'C':sum(r['accepted']and r['identity']==r['predicted_id']for r in known),'W':sum(r['accepted']and r['identity']!=r['predicted_id']for r in known),'U':sum(not r['accepted']for r in known),'unknown_FA':sum(r['accepted']for r in unknown)}
  assert summary==next(x for x in outcomes if x['model']==name and x['policy']==policy);assert summary['C']+summary['W']+summary['U']==30;derivedout.append(summary)
assert idcells==1200 and top1changes==state['Top1_changes']and top5changes==state['Top5_order_changes']and rankingchanges==state['full_ranking_changes']and decisionchanges==state['fixed_decision_changes']
numericfailed=sum(r['numeric_failed_images']for r in state['models'].values());assert numericfailed==state['numeric_failed_images']
expected_status='BOTH90_ENCODERS180_ARM_FEATURES_AND480_FIXED_DECISIONS_PASS'if not(numericfailed or top1changes or top5changes or decisionchanges)else'ALL180_FEATURES_SAVED_BUT_NUMERIC_OR_RANK_OR_DECISION_GATE_FAILED';assert state['status']==expected_status
prep_ms=[r['JPEG_read_decode_preprocess_ms']for r in pre['rows']]
result={'status':'ALL90_ARM_INPUTS180_ACTUAL_FEATURES1200_ID_SCORES480_DECISIONS_TIMING_AND_TERMINAL_STATE_INDEPENDENTLY_RECOMPUTED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'experiment_status':state['status'],'actual_ARM_measured_forwards':180,'actual_ARM_warmup_forwards':4,'actual_ARM_network_calls':184,'new_PL_forwards':0,'source_JPEG_and_tensor_hashes_verified':90,'input_anchors_verified':6,'actual_raw_features_verified':180,'ID_score_cells_recomputed':1200,'retrieval_queries':120,'fixed_decisions':480,
 'numeric_failed_images':numericfailed,'Top1_changes':top1changes,'Top5_order_changes':top5changes,'full_ranking_changes':rankingchanges,'decision_changes':decisionchanges,'maximum_normalized_feature_error':max(allerrs),'timings':timings,
 'JPEG_read_decode_preprocess_mean_ms':float(np.mean(prep_ms)),'JPEG_read_decode_preprocess_P95_ms':float(np.quantile(prep_ms,.95)),'primary_outcomes':[r for r in derivedout if r['policy']=='primary_cal10_fold0'],
 'archive_bytes':t['bytes'],'archive_SHA256':t['sha256'],'archive_members':len(members),'manifest_files':len(manifest),'verification_additional_model_forwards':0,'new_training_updates':0,'default_model_or_threshold_changed':False,'new_independent_identity_test':False,'concurrent_detector_or_full5FPS_test':False,'whole_goal_complete':False}
(ROOT/'results').mkdir(exist_ok=True);save(ROOT/'results/independent_verification.json',result);print(json.dumps(result),flush=True)
