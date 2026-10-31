from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import hashlib,json,tarfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

meta=load(ROOT/'evidence/reference_transfer.json');a=ROOT/'verification_delivery_v1.tar.gz';assert a.stat().st_size==meta['bytes']and sha(a)==meta['sha256'];out=ROOT/'reference_delivery';out.mkdir(exist_ok=False)
with tarfile.open(a)as tar:
 members=tar.getmembers();assert len(members)==meta['members']
 for row in members:
  rel=PurePosixPath(row.name);assert row.isfile()and not rel.is_absolute()and'..'not in rel.parts
  p=(out/row.name).resolve();assert p.is_relative_to(out.resolve())and not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(row).read())
for row in load(out/'result_manifest.json'):assert sha(out/row['file'])==row['sha256']and(out/row['file']).stat().st_size==row['bytes']
p=load(ROOT/'protocol/reference_v1.json');e=load(ROOT/'protocol/reference_execution_v1.json');s=load(out/'results/reference/summary.json');tracker=load(out/'results/tracker_replay/summary.json')
assert s['status']=='ALL_UNIQUE_TRIGGER_PHOTOS_AND_BOTH30_GALLERIES_TORCH_REFERENCE_AND_FIXED_DECISIONS_PASS'and s['actual_Torch_image_forwards']==p['expected_Torch_image_forwards']
assert sha(ROOT/'protocol/reference_v1.json')==sha(out/'protocol/reference_v1.json')
for file,digest in e['code_sha256'].items():assert sha(ROOT/file)==sha(out/file)==digest
qcheck=load(out/'results/reference/query_checks.json');gcheck=load(out/'results/reference/gallery_checks.json');ret=load(out/'results/reference/retrieval_checks.json');images=p['gallery_images'];labels=p['registered_IDs'];checked=0;errors=[]
with np.load(ROOT/'reference_input/actual_galleries.npz')as ar:actualgallery={k:ar[k].copy()for k in ar.files}
with np.load(out/'results/reference/all_features.npz')as ar:
 for name in['old','new']:
  gallery=ar[name+'_gallery_normalized'];raw=ar[name+'_gallery_raw'];assert gallery.shape==raw.shape==(30,576)
  norm=raw.astype(float)/np.linalg.norm(raw.astype(float),axis=1)[:,None];assert np.max(np.abs(norm-gallery))<1e-7
  for i in range(30):
   c=next(r for r in gcheck if r['model']==name and r['index']==i);delta=float(np.max(np.abs(gallery[i]-actualgallery[name][i])));assert delta==c['maximum_normalized_difference']and delta<=1e-4;errors.append(delta)
  rows=[r for r in p['queries']if r['model']==name];qraw=ar[name+'_query_raw'];qnorm=ar[name+'_query_normalized'];assert qraw.shape==qnorm.shape==(len(rows),576)
  assert np.max(np.abs(qraw.astype(float)/np.linalg.norm(qraw.astype(float),axis=1)[:,None]-qnorm))<1e-7
  for position,row in enumerate(rows):
   with np.load(ROOT/row['vector_file'])as data:actual=data['normalized'].copy();scores=data['scores'].copy()
   c=next(r for r in qcheck if r['model']==name and r['query_index']==row['query_index']);delta=float(np.max(np.abs(qnorm[position]-actual)));distance=1-float(qnorm[position].astype(float)@actual.astype(float))
   assert delta==c['maximum_normalized_difference']and abs(distance-c['one_minus_dot'])<2e-15 and delta<=1e-4 and distance<=1e-5;errors.append(delta)
   for kind,g in[('same_actual_ARM_gallery',actualgallery[name]),('fresh_Torch_gallery',gallery)]:
    values={ID:max(float(np.dot(qnorm[position].astype(float),g[j].astype(float)))for j,r in enumerate(images)if r['identity']==ID)for ID in labels};winner=sorted(labels,key=lambda ID:(-values[ID],ID))[0]
    for policy,tau in p['thresholds'].items():
     rr=next(x for x in ret if x['model']==name and x['query_index']==row['query_index']and x['gallery']==kind and x['policy']==policy)
     assert rr['predicted_id']==winner and rr['accepted']==(values[winner]>=tau)and rr['same_as_actual_ARM']
     assert all(abs(rr['all_scores'][j]-values[ID])<1e-12 for j,ID in enumerate(labels));checked+=1
assert checked==4*p['unique_model_input_queries']and len(qcheck)==p['unique_model_input_queries']and len(gcheck)==60
assert tracker['status']=='ALL4_FULL_TRACKER_ASSOCIATION_AND_EVENT_REPLAYS_MATCH_ACTUAL_ARM_WITH_FROZEN_TOLERANCES'
assert tracker['observation_ticks']==load(ROOT/'results/independent_verification.json')['counter_observation_ticks_with_history']
v={'status':'TRIGGER_PAIR_ALL_UNIQUE_TORCH_FEATURES_BOTH_GALLERIES_FIXED_SCORES_AND4_FULL_TRACKER_REPLAYS_INDEPENDENTLY_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),'Slurm_job_id':s['Slurm_job_id'],'actual_Torch_image_forwards':s['actual_Torch_image_forwards'],'unique_model_input_queries':p['unique_model_input_queries'],'actual_query_jobs_represented':p['actual_job_count'],'gallery_image_forwards':60,'network_calls':s['network_calls'],'warmups':0,'maximum_normalized_error':max(errors),'retrieval_decisions_checked':checked,'tracker_replay_observation_ticks':tracker['observation_ticks'],'tracker_replay_counter_paths':8,'verification_additional_model_forwards':0,'new_training_updates':0,'whole_goal_complete':False};f=ROOT/'results/reference_independent_verification.json';assert not f.exists();f.write_bytes(json.dumps(v,indent=2).encode()+bytes([10]));print(json.dumps(v))
