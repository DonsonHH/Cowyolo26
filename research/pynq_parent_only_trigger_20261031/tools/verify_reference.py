"""Independently rescore 25 queries and prove exact feature-cache provenance."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parents[1];REF=ROOT/'reference_delivery'
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=load(ROOT/'protocol/reference_v1.json');remote=load(REF/'protocol/reference_v1.json')
assert sha(ROOT/'protocol/reference_v1.json')==sha(REF/'protocol/reference_v1.json')
for row in p['files']:assert sha(ROOT/row['file'])==sha(REF/row['file'])==row['sha256']
for name,digest in p['code_sha256'].items():assert sha(ROOT/name)==sha(REF/name)==digest
prior_p=load(REF/'reference_input/prior_reference_protocol.json')
assert sha(REF/'reference_input/prior_reference_protocol.json')==p['prior_reference_protocol_sha256']
assert sha(REF/'reference_input/prior_reference_review.json')==p['prior_reference_review_sha256']
assert p['gallery_images']==prior_p['gallery_images']and p['registered_IDs']==prior_p['registered_IDs']
for model in p['models']:
 old=next(row for row in prior_p['models']if row['name']==model['name'])
 assert model['checkpoint_sha256']==old['checkpoint_sha256']
s=load(REF/'results/reference/summary.json');checks=load(REF/'results/reference/query_checks.json')
gchecks=load(REF/'results/reference/gallery_checks.json');retrieval=load(REF/'results/reference/retrieval_checks.json')
assert s['status']=='REFERENCE_COMPLETE_ALL_NUMERICS_AND_FIXED_DECISIONS_MATCH'
assert s['actual_Torch_image_forwards']==s['network_calls']==p['expected_new_Torch_image_forwards']==13
assert s['new_gallery_image_forwards']==s['warmups']==0 and s['reused_gallery_vectors']==60
assert s['reused_unique_query_features']==p['expected_reused_query_features']==12
assert s['unique_model_input_queries']==len(checks)==25 and s['actual_query_jobs_represented']==40
assert len(gchecks)==60 and len(retrieval)==s['retrieval_comparisons']==100
assert s['numeric_failures']==s['retrieval_failures']==0
assert s['Slurm_job_id']==(REF/'reference_job_id.txt').read_text().strip()
assert f"{s['Slurm_job_id']}|cow-parent-trigger|COMPLETED|0:0|"in(REF/'logs/reference_sacct.txt').read_text()
assert not(REF/f"logs/verify-{s['Slurm_job_id']}.err").read_text().strip()
with np.load(REF/'reference_input/prior_all_features.npz')as a:prior={key:a[key].copy()for key in a.files}
with np.load(REF/'results/reference/all_features.npz')as a:current={key:a[key].copy()for key in a.files}
with np.load(REF/'reference_input/actual_galleries.npz')as a:actual_galleries={key:a[key].copy()for key in a.files}
new=reused=decisions=0;errors=[]
for name in['old','new']:
 gal=current[name+'_gallery_normalized'];raw=current[name+'_gallery_raw']
 assert gal.tobytes()==prior[name+'_gallery_normalized'].tobytes()and raw.tobytes()==prior[name+'_gallery_raw'].tobytes()
 assert np.max(np.abs(raw.astype(float)/np.linalg.norm(raw.astype(float),axis=1)[:,None]-gal))<1e-7
 for i in range(30):
  record=next(row for row in gchecks if row['model']==name and row['index']==i)
  delta=float(np.max(np.abs(gal[i]-actual_galleries[name][i])))
  assert delta==record['maximum_normalized_difference']and delta<=1e-4 and not record['new_forward']
 rows=[row for row in p['queries']if row['model']==name]
 qraw=current[name+'_query_raw'];qnorm=current[name+'_query_normalized']
 assert qraw.shape==qnorm.shape==(len(rows),576)
 assert np.max(np.abs(qraw.astype(float)/np.linalg.norm(qraw.astype(float),axis=1)[:,None]-qnorm))<1e-7
 for position,row in enumerate(rows):
  with np.load(ROOT/row['vector_file'])as a:actual=a['normalized'].copy();actual_scores=a['scores'].copy()
  check=next(item for item in checks if item['query_index']==row['query_index']and item['model']==name)
  cached=row['cached_reference']
  if cached is None:
   new+=1;assert check['reference_origin']=='new_Torch_query_forward'
  else:
   reused+=1;assert check['reference_origin']=='reused_verified_same_checkpoint_and_input'
   assert cached['raw_array']==name+'_'+cached['kind']+'_raw'
   assert cached['normalized_array']==name+'_'+cached['kind']+'_normalized'
   source_rows=prior_p['gallery_images']if cached['kind']=='gallery'else[q for q in prior_p['queries']if q['model']==name]
   assert source_rows[cached['position']]['input_tensor_sha256']==row['input_tensor_sha256']
   assert qraw[position].tobytes()==prior[cached['raw_array']][cached['position']].tobytes()
   assert qnorm[position].tobytes()==prior[cached['normalized_array']][cached['position']].tobytes()
  delta=float(np.max(np.abs(qnorm[position]-actual)));dot=1-float(qnorm[position].astype(float)@actual.astype(float))
  assert delta==check['maximum_normalized_difference']and abs(dot-check['one_minus_dot'])<2e-15
  assert delta<=1e-4 and dot<=1e-5 and check['numeric_pass'];errors.append(delta)
  for kind,g in[('same_actual_ARM_gallery',actual_galleries[name]),('reused_verified_Torch_gallery',gal)]:
   scores=np.array([max(float(np.dot(qnorm[position].astype(float),g[j].astype(float)))for j,item in enumerate(p['gallery_images'])if item['identity']==identity)for identity in p['registered_IDs']])
   winner=int(np.argmax(scores))
   for policy,tau in p['thresholds'].items():
    record=next(item for item in retrieval if item['model']==name and item['query_index']==row['query_index']and item['gallery']==kind and item['policy']==policy)
    assert record['predicted_id']==p['registered_IDs'][winner]and record['accepted']==(scores[winner]>=tau)
    assert record['same_as_actual_ARM']and record['predicted_id']==row['predicted_id']
    assert np.max(np.abs(scores-record['all_scores']))<1e-12
    assert record['maximum_ID_score_difference']==float(np.max(np.abs(scores-actual_scores)))
    decisions+=1
assert new==13 and reused==12 and decisions==100
jobs=load(ROOT/'results/actual_job_rows.json');assignments=p['actual_job_assignments']
assert len(jobs)==len(assignments)==40
for job,assignment in zip(jobs,assignments):
 assert job['run']==assignment['run']and job['identity_model']==assignment['model']and job['event']==assignment['event']
 row=p['queries'][assignment['query_index']]
 assert job['input_tensor_sha256']==assignment['input_tensor_sha256']==row['input_tensor_sha256']and row['model']==job['identity_model']
result={'status':'ALL25_QUERY_FEATURES13_NEW12_REUSED_BOTH60_REUSED_GALLERY_VECTORS_AND100_FIXED_DECISIONS_VERIFIED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'Slurm_job_id':s['Slurm_job_id'],
 'new_Torch_image_forwards':13,'new_gallery_image_forwards':0,'reused_gallery_vectors':60,'reused_unique_query_features':12,
 'unique_model_input_queries':25,'actual_query_jobs_represented':40,'fixed_retrieval_decisions_checked':100,
 'maximum_query_normalized_error':max(errors),'maximum_gallery_normalized_error':s['maximum_gallery_normalized_error'],
 'feature_cache_checkpoint_and_input_provenance_verified':True,'new_model_forwards_by_verification':0,
 'permanent_identity_accuracy_known':False,'whole_goal_complete':False}
with(ROOT/'results/reference_independent_verification.json').open('x',encoding='utf-8')as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
