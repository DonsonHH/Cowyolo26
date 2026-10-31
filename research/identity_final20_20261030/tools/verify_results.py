"""Independent scalar score, decision, grouping and resampling audit; no inference."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import hashlib,importlib.util,json,zlib
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OUT=ROOT/'delivery/results/evaluation'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n')

p=load(ROOT/'protocol/run_v1.json');e=load(ROOT/'protocol/execution_v1.json');s=load(OUT/'summary.json');assert s['status']=='BOTH_FROZEN_ENCODERS90_FINAL_ID_IMAGES180_FORWARDS8_FIXED_POLICIES_AND20_PAIRED_ID_CONTRASTS_COMPLETE'
assert s['actual_model_image_forwards']==180 and s['actual_network_calls']==16 and s['warmups']==0 and s['new_training_updates']==0
first=load(ROOT/'evidence/first_final_ID_pixel_request_gate.json');assert e['created_UTC']<first['created_UTC']<s['created_UTC']
assert e['protocol_sha256']==sha(ROOT/'protocol/run_v1.json')==s['protocol_sha256']and sha(ROOT/'protocol/execution_v1.json')==s['execution_sha256']==first['execution_sha256']
for name,digest in e['files_sha256'].items():assert sha(ROOT/name)==sha(ROOT/'delivery'/name)==digest
spec=importlib.util.spec_from_file_location('final20_independent_body',ROOT/'tools/frozen_body_tensor.py');body=importlib.util.module_from_spec(spec);spec.loader.exec_module(body)
inputs=load(OUT/'input_hashes.json');admission=load(ROOT/'results/pixel_admission.json');assert len(inputs)==len(admission['rows'])==len(p['images'])==90
pixelhashes={};grouped=defaultdict(list)
for index,(row,audit,h)in enumerate(zip(p['images'],admission['rows'],inputs)):
 file=ROOT/row['local_relative_file'];data=file.read_bytes();assert hashlib.sha256(data).hexdigest()==audit['sha256']and len(data)==row['zip_entry']['uncompressed_size']and zlib.crc32(data)&0xffffffff==row['zip_entry']['CRC32']
 with Image.open(file)as image:image.load();rgb=image.convert('RGB');x=body.body_tensor(rgb)
 digest=hashlib.sha256(rgb.width.to_bytes(4,'big')+rgb.height.to_bytes(4,'big')+rgb.tobytes()).hexdigest();assert digest==audit['canonical_pixel_sha256'];pixelhashes[index]=digest
 assert hashlib.sha256(x.tobytes()).hexdigest()==h['input_tensor_sha256']and h['index']==index
 if index in e['tensor_anchor_indices']:
  with np.load(OUT/'input_anchors'/('index'+str(index)+'.npz'))as a:assert a['input'].tobytes()==x.tobytes()
 assert row['date']<='2020-03-04'and row['day_gap']>=7;grouped[(row['publisher_identity'],row['purpose'])].append(index)
assert len(set(pixelhashes.values()))==90 and all(len(v)==3 for v in grouped.values())
training=load(PROJECT/'identity_domain_adapt_20261030/results/acquisition.json');development=load(PROJECT/'cows2021_identity_eval_20261030/results/pixel_admission.json')
prior={r['canonical_pixel_sha256']for r in training['records']}|{r['canonical_pixel_sha256']for r in development['rows']};assert set(pixelhashes.values()).isdisjoint(prior)
domain=load(PROJECT/'identity_domain_adapt_20261030/protocol/run_v1.json');IDs=set(p['roles']['registered']+p['roles']['unknown']);assert IDs.isdisjoint(domain['Cows_training_IDs'])and IDs.isdisjoint(domain['prior_Cows_calibration_development_IDs'])
assert list(p['roles']['registered']+p['roles']['unknown'])==domain['future_final_ID_candidates_pixels_closed']
gi=[i for i,row in enumerate(p['images'])if row['purpose']=='gallery'];qi=[i for i,row in enumerate(p['images'])if row['purpose']!='gallery'];labels=sorted(p['roles']['registered'])
outcomes=load(OUT/'all_outcomes.json');decisions=load(OUT/'all_decisions.json');intervals=load(OUT/'per_ID_intervals.json');contrasts=load(OUT/'paired_ID_differences.json');assert len(outcomes)==8 and len(decisions)==480 and len(contrasts)==20
with np.load(OUT/'bootstrap_ID_indices.npz')as a:known_draws=a['known'].copy();unknown_draws=a['unknown'].copy()
rng=np.random.default_rng(e['bootstrap_seed']);assert np.array_equal(known_draws,rng.integers(0,10,size=(2000,10)))and np.array_equal(unknown_draws,rng.integers(0,10,size=(2000,10)))
derived={};id_scores=decisions_checked=0
for model in['old_C','new_C_domain_seed26']:
 with np.load(OUT/model/'all_features.npz')as a:raw=a['raw'].copy();features=a['normalized'].copy()
 assert raw.shape==features.shape==(90,576)and np.isfinite(raw).all()and np.isfinite(features).all()
 normalized=raw.astype(float)/np.sqrt(np.sum(raw.astype(float)**2,axis=1))[:,None];assert np.max(np.abs(normalized-features))<1e-7
 unthresholded=load(OUT/model/'retrieval_unthresholded.json');assert len(unthresholded)==60
 own=[]
 for index in qi:
  scores={label:max(float(np.dot(features[index].astype(float),features[j].astype(float)))for j in gi if p['images'][j]['publisher_identity']==label)for label in labels};order=sorted(labels,key=lambda label:(-scores[label],label));original=next(r for r in unthresholded if r['source_index']==index)
  assert original['predicted_id']==order[0]and original['top5_IDs']==order[:5]
  assert all(abs(original['all_ID_scores'][label]-scores[label])<1e-12 for label in labels)
  assert abs(original['score']-scores[order[0]])<1e-12;id_scores+=10
  own.append({**original,'scalar_recomputed_scores':scores})
 for policy,tau in e['threshold_policies'][model].items():
  expected=[r for r in decisions if r['model']==model and r['policy']==policy];assert len(expected)==60
  for row,original in zip(own,expected):
   assert row['source_index']==original['source_index']and row['predicted_id']==original['predicted_id']
   # Preserve the canonical saved score; the independently scalar recomputed
   # value above has a1e-12 gate. No threshold endpoint is moved by this audit.
   assert original['threshold']==tau and original['accepted']==(row['score']>=tau);decisions_checked+=1
  known=[r for r in expected if r['is_known']];unknown=[r for r in expected if not r['is_known']]
  c=sum(r['accepted']and r['predicted_id']==r['identity']for r in known);w=sum(r['accepted']and r['predicted_id']!=r['identity']for r in known);u=sum(not r['accepted']for r in known);fa=sum(r['accepted']for r in unknown)
  summary=next(r for r in outcomes if r['model']==model and r['policy']==policy)
  assert[summary[k]for k in['C','W','U','unknown_FA']]==[c,w,u,fa]and c+w+u==30
  assert summary['known_Top1']==sum(r['identity']==r['predicted_id']for r in known)and summary['known_Top5']==sum(r['identity']in r['top5_IDs']for r in known)
  wrong=(w+fa)/(c+w+fa)if c+w+fa else None;assert summary['accepted_wrong_fraction']==wrong
  own_intervals={}
  for metric,is_known in[('Top1',True),('C',True),('W',True),('U',True),('FA',False)]:
   identities=sorted(p['roles']['registered']if is_known else p['roles']['unknown']);rates=[]
   for identity in identities:
    rr=[r for r in expected if r['identity']==identity];assert len(rr)==3
    if metric=='Top1':n=sum(r['predicted_id']==identity for r in rr)
    elif metric=='C':n=sum(r['accepted']and r['predicted_id']==identity for r in rr)
    elif metric=='W':n=sum(r['accepted']and r['predicted_id']!=identity for r in rr)
    elif metric=='U':n=sum(not r['accepted']for r in rr)
    else:n=sum(r['accepted']for r in rr)
    rates.append(n/3)
   arr=np.array(rates);draw=known_draws if is_known else unknown_draws
   sample=np.array([sum(rates[j]for j in row)/10 for row in draw]);saved=intervals[model+':'+policy][metric]
   assert saved['IDs']==identities and saved['rates']==rates and abs(saved['macro_mean']-float(arr.mean()))<1e-15
   assert np.max(np.abs(np.array(saved['percentile95'])-np.quantile(sample,[.025,.975])))<1e-15
   own_intervals[metric]=rates
  derived[model+':'+policy]=own_intervals
for row in contrasts:
 metric=row['metric'];a=np.array(derived['old_C:'+row['policy']][metric]);b=np.array(derived['new_C_domain_seed26:'+row['policy']][metric]);delta=b-a;draw=unknown_draws if metric=='FA'else known_draws
 assert np.array_equal(delta,np.array(row['new_minus_old_per_ID']))and abs(float(delta.mean())-row['mean_difference'])<1e-15
 sample=np.array([sum(delta[j]for j in rr)/10 for rr in draw]);assert np.max(np.abs(np.quantile(sample,[.025,.975])-row['percentile95']))<1e-15
assert id_scores==1200 and decisions_checked==480
result={'status':'FINAL20_ALL90_SOURCE_INPUTS180_RAW_FEATURES1200_ID_SCORES480_DECISIONS8_INTERVALS20_PAIRED_CONTRASTS_INDEPENDENTLY_RECOMPUTED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'image_inputs':90,'model_image_forwards':180,'network_calls':16,'input_tensor_anchors':6,'identity_score_cells':1200,'decisions':480,'per_ID_interval_sets':8,'paired_ID_contrasts':20,'new_model_forwards_by_verification':0,
 'main_outcomes':[r for r in outcomes if r['policy']=='primary_cal10_fold0'],'same_scene_component_identity_namespace_disjointness_only':True,'unknown_and_perfect_Top1_bootstrap_boundaries_not_population_guarantees':True,
 'final20_IDs_now_seen':True,'reservedMar05toMar11_pixels_opened':False,'current12_passage_permanent_ID_GT_obtained':False,'new_default_model_or_threshold_adopted':False,'whole_goal_complete':False}
save(ROOT/'results/independent_verification.json',result);print(json.dumps(result),flush=True)
