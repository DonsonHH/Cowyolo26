"""Separate update schedule and scalar retrieval/calibration audit from raw artifacts."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import hashlib,json,math,random
import numpy as np

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent


def load(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


plan=load(ROOT/'protocol/run_v1.json');execution=load(ROOT/'protocol/execution_v1.json')
assert sha(ROOT/'protocol/run_v1.json')==execution['protocol_sha256']
for name,digest in execution['files_sha256'].items():assert sha(ROOT/name)==digest
for row in load(ROOT/'delivery/result_manifest.json'):assert sha(ROOT/'delivery'/row['file'])==row['sha256']
future=set(plan['future_final_ID_candidates_pixels_closed']);current=set(plan['Cows_training_IDs']);oldIDs=set(sum(plan['prior_Cows_calibration_development_IDs'].values(),[]))
assert len(future)==20 and len(current)==16 and not(current&future or current&oldIDs or future&oldIDs)
assert{path.parent.name for path in(ROOT/'input/cows_train').rglob('*.jpg')}==current
updates=training_images=0;initial_digests=set();all_step_checks=[]
for condition in plan['conditions']:
 folder=ROOT/'delivery/results/training'/condition['name'];terminal=load(folder/'terminal.json')
 assert terminal['status']=='ONE_DOMAIN_TRAINING_CONDITION_COMPLETE'and terminal['optimizer_updates']==terminal['network_calls']==300
 assert sha(folder/'last_encoder.pt')==terminal['last_encoder_sha256']
 assert terminal['final_encoder_state_digest']!=terminal['initial_encoder_state_digest'];initial_digests.add(terminal['initial_encoder_state_digest'])
 journals=[json.loads(line)for line in(folder/'actual_updates.jsonl').read_text().splitlines()];assert len(journals)==300 and sha(folder/'actual_updates.jsonl')==terminal['updates_journal_sha256']
 rows=plan['MultiCam_training_images']if condition['arm']=='M_continue'else plan['Cows_training_images'];byID=defaultdict(list)
 for index,row in enumerate(rows):byID[row['identity']].append(index)
 rng=random.Random(condition['seed']);ids=sorted(byID)
 for step,journal in enumerate(journals,1):
  batch=[]
  for identity in rng.sample(ids,8):
   days=defaultdict(list)
   for index in byID[identity]:days[rows[index]['day']].append(index)
   selected_days=rng.sample(sorted(days),2);chosen=[rng.choice(days[day])for day in selected_days]
   chosen+=rng.sample([index for index in byID[identity]if index not in chosen],2);batch.extend(chosen)
  assert batch==journal['source_image_indices']and journal['update']==step
  assert journal['identity_labels']==[rows[index]['identity']for index in batch]and journal['dates']==[rows[index]['day']for index in batch]
  for start in range(0,32,4):
   selected=batch[start:start+4];assert len(set(selected))==4 and len({rows[index]['identity']for index in selected})==1 and len({rows[index]['day']for index in selected})>=2
  assert all(math.isfinite(journal[key])for key in['loss','CE','triplet'])and abs(journal['loss']-journal['CE']-journal['triplet'])<2e-6
  assert journal['gradient_tensors']>=journal['nonzero_gradient_tensors']>0
  assert journal['cumulative_training_image_forwards']==step*32
 with np.load(folder/'first4_actual_training_inputs.npz')as archive:
  assert archive['input'].shape==(4,3,224,224)and archive['input'].dtype==np.float32 and np.isfinite(archive['input']).all()
 updates+=300;training_images+=terminal['training_image_forwards'];all_step_checks.append({'condition':condition['name'],'updates':300,'images':9600,'all_sampled_indices_and_cross_date_positive_groups_reproduced':True})
assert len(initial_digests)==1 and updates==1800 and training_images==57600
smoke=load(ROOT/'delivery/results/smoke/summary.json');assert smoke['discarded_optimizer_updates']==2 and smoke['source_image_forwards']==64
evaluation=ROOT/'delivery/results/evaluation';summary=load(evaluation/'summary.json')
assert summary['actual_evaluation_model_image_forwards']==3780 and summary['actual_network_calls']==318 and summary['warmup_forwards']==0
weight_freeze=load(evaluation/'all6_last_checkpoints_frozen.json');threshold_freeze=load(evaluation/'all6_thresholds_frozen.json')
assert sha(evaluation/'all6_last_checkpoints_frozen.json')==summary['weight_freeze_SHA256']
assert sha(evaluation/'all6_thresholds_frozen.json')==summary['threshold_freeze_SHA256']
assert weight_freeze['new_evaluation_model_image_forwards_at_freeze']==0 and threshold_freeze['development_feature_forwards']==0
assert threshold_freeze['calibration_image_forwards']==1080
t1=datetime.fromisoformat(weight_freeze['created_UTC']);t2=datetime.fromisoformat(threshold_freeze['created_UTC'])
assert all(datetime.fromisoformat(row['finished_UTC'])>t1 and(datetime.fromisoformat(row['finished_UTC'])<t2 if row['phase']=='calibration'else datetime.fromisoformat(row['finished_UTC'])>t2)for row in summary['timeline'])
source_plan=load(PROJECT/'cows2021_identity_eval_20261030/protocol/run_v1.json');source_rows=[{**row,'identity':row['identity_namespace'],'day':row['date'],'source_index':index}for index,row in enumerate(source_plan['selected_images'])]
calrows=[row for row in source_rows if row['phase']=='calibration'];devrows=[row for row in source_rows if row['phase']=='evaluation']
retention=[]
for index,row in enumerate(plan['MultiCam_retention_images']):
 retention.append({**row,'source_index':index,'purpose':'gallery'if row['split']=='evaluation_gallery'else'query','is_known':row['role']=='evaluation_registered_ids'})
input_hashes={};features_checked=score_cells=decisions_checked=0;checks=[];raw_by_condition={}


def score_rows(features,rows,predictions,gallery_ids=None):
 global score_cells
 gallery=[i for i,row in enumerate(rows)if row['purpose']=='gallery'and(gallery_ids is None or row['identity']in gallery_ids)]
 position={row['source_index']:i for i,row in enumerate(rows)}
 for prediction in predictions:
  qi=position[prediction['source_index']];independent={}
  for gi in gallery:
   value=float(np.dot(features[qi].astype(float),features[gi].astype(float)));identity=rows[gi]['identity'];independent[identity]=max(value,independent.get(identity,-1.))
  assert set(independent)==set(prediction['scores_by_ID'])
  assert max(abs(independent[key]-prediction['scores_by_ID'][key])for key in independent)<1e-12
  order=sorted(independent,key=lambda key:(-independent[key],key));assert order[0]==prediction['predicted_id']and order[:5]==prediction['top5_IDs']
  assert abs(independent[order[0]]-prediction['similarity'])<1e-12
  assert prediction['identity']==rows[qi]['identity']and prediction['is_known']==rows[qi]['is_known'];score_cells+=len(independent)


def counts(rows):
 known=[row for row in rows if row['is_known']];unknown=[row for row in rows if not row['is_known']]
 return{'known_queries':len(known),'unknown_queries':len(unknown),
        'known_correct_accepted_C':sum(row['accepted']and row['predicted_id']==row['identity']for row in known),
        'known_wrong_accepted_W':sum(row['accepted']and row['predicted_id']!=row['identity']for row in known),
        'known_rejected_U':sum(not row['accepted']for row in known),
        'known_closed_top1_correct':sum(row['predicted_id']==row['identity']for row in known),
        'unknown_false_accepts':sum(row['accepted']for row in unknown)}


for condition in plan['conditions']:
 name=condition['name'];phase_features={}
 for phase,rows in[('calibration',calrows),('development',devrows),('retention',retention)]:
  folder=evaluation/phase/name
  with np.load(folder/'features.npz')as archive:raw=archive['raw'].copy();normalized=archive['normalized'].copy()
  assert raw.shape==normalized.shape==(len(rows),576)and raw.dtype==np.float32 and np.isfinite(raw).all()
  assert np.max(np.abs(raw.astype(float)/np.sqrt(np.sum(raw.astype(float)**2,axis=1))[:,None]-normalized))<1e-7
  hashes=load(folder/'input_hashes.json');assert len(hashes)==len(rows)
  for source,entry in zip(rows,hashes):
   key=(phase,source['source_index']);assert source['source_index']==entry['source_index']
   if key in input_hashes:assert input_hashes[key]==entry['input_tensor_sha256']
   else:input_hashes[key]=entry['input_tensor_sha256']
  phase_features[phase]=normalized;features_checked+=len(rows)
 cal=load(evaluation/'calibration'/name/'retrieval.json');score_rows(phase_features['calibration'],calrows,cal)
 taus=sorted({row['similarity']for row in cal}|{float(np.nextafter(max(row['similarity']for row in cal),np.inf))});legal=[]
 for tau in taus:
  values=counts([{**row,'accepted':row['similarity']>=tau}for row in cal])
  if values['unknown_false_accepts']<=3:legal.append((values['known_correct_accepted_C'],-values['known_wrong_accepted_W'],tau))
 expected_tau=max(legal)[2];frozen=next(row for row in threshold_freeze['calibration']if row['condition']==name);assert expected_tau==frozen['threshold']['threshold']
 for outcome in[row for row in summary['outcomes']if row['condition']==name]:
  if outcome['dataset']=='Cows2021':
   ids=['Cows2021_IdentificationTest:'+identity for identity in source_plan['roles']['evaluation_registered']]
   if outcome['scope']=='fold0':ids=ids[:20]
   elif outcome['scope']=='fold1':ids=ids[20:]
   folder=evaluation/'development'/name;decided=load(folder/(outcome['scope']+'_'+outcome['threshold_policy']+'_decisions.json'));values=phase_features['development'];rows=devrows
   expected_query_indices=[row['source_index']for row in rows if row['purpose']!='gallery'and(not row['is_known']or row['identity']in ids)]
  else:
   ids=None;folder=evaluation/'retention'/name;decided=load(folder/'original_threshold_decisions.json');values=phase_features['retention'];rows=retention
   expected_query_indices=[row['source_index']for row in rows if row['purpose']!='gallery']
  assert expected_query_indices==[row['source_index']for row in decided]
  tau=expected_tau if outcome['threshold_policy']=='Cows_calibrated'else plan['original_threshold'];assert tau==outcome['threshold']
  assert all(row['accepted']==(row['similarity']>=tau)for row in decided);score_rows(values,rows,decided,ids)
  actual=counts(decided)
  for key,value in actual.items():assert outcome['metrics'][key]==value
  per=[]
  for identity in sorted({row['identity']for row in decided}):
   group=[row for row in decided if row['identity']==identity];known=group[0]['is_known']
   per.append({'identity':identity,'is_known':known,'queries':len(group),'closed_top1_accuracy':sum(row['predicted_id']==identity for row in group)/len(group)if known else None,
               'correct_accepted_rate':sum(row['accepted']and row['predicted_id']==identity for row in group)/len(group)if known else None,
               'false_accept_rate':sum(row['accepted']for row in group)/len(group)if not known else None})
  assert per==outcome['metrics']['per_identity'];rng=np.random.default_rng(26)
  for field,known in[('closed_top1_accuracy',True),('correct_accepted_rate',True),('false_accept_rate',False)]:
   data=np.array([row[field]for row in per if row['is_known']==known]);means=np.array([data[rng.integers(0,len(data),len(data))].mean()for _ in range(2000)])
   np.testing.assert_allclose(np.quantile(means,[.025,.975]),outcome['ID_cluster_intervals'][field]['percentile_95_interval'],rtol=0,atol=1e-12)
  checks.append({'condition':name,'dataset':outcome['dataset'],'scope':outcome['scope'],'threshold_policy':outcome['threshold_policy'],**actual});decisions_checked+=len(decided)
assert features_checked==3780 and len(checks)==42 and decisions_checked==7560
result={'status':'SIX_TRAINING_SCHEDULES1800_UPDATES3780_FEATURES42_OUTCOMES_AND7560_DECISIONS_INDEPENDENTLY_RECOMPUTED',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'formal_updates_checked':updates,'formal_training_image_forwards':training_images,
        'discarded_smoke_updates':2,'smoke_training_image_forwards':64,'evaluation_feature_vectors':features_checked,
        'evaluation_decisions':decisions_checked,'ID_score_cells_checked':score_cells,'same_input_hashes_across6_models':len(input_hashes),
        'all6_same_start_encoder_state':True,'all6_last_checkpoints_before_calibration':True,'all6_thresholds_before_development_and_retention':True,
        'bootstrap2000_by_ID_all42_outcomes_reproduced':True,'future20_ID_pixels_opened':False,
        'new_model_forwards_by_verification':0,'new_training_updates_by_verification':0,'outcomes':checks,'training':all_step_checks,'whole_goal_complete':False}
p=ROOT/'results/independent_verification.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({key:value for key,value in result.items()if key not in['outcomes','training']}))
