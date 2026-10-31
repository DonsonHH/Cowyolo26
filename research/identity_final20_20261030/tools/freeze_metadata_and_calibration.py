"""No JPEG requests or forward calls: seal ID metadata and cached calibration scores."""
from pathlib import Path
from datetime import date,datetime,timezone
from collections import defaultdict
import hashlib,json
import numpy as np

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(v,indent=2)+'\n').encode())

domain=load(PROJECT/'identity_domain_adapt_20261030/protocol/run_v1.json');old=load(PROJECT/'cows2021_identity_eval_20261030/protocol/run_v1.json')
future=domain['future_final_ID_candidates_pixels_closed'];assert len(future)==len(set(future))==20
assert set(future).isdisjoint(domain['Cows_training_IDs'])and set(future).isdisjoint(domain['prior_Cows_calibration_development_IDs'])
rows=load(PROJECT/'cows2021_identity_intake_20261030/results/test8670_members.json');byid=defaultdict(lambda:defaultdict(list))
for row in rows:
 if row['publisher_identity']in future and row['date']<='2020-03-04':byid[row['publisher_identity']][row['date']].append(row)

def three(images):
 sessions=defaultdict(list)
 for image in images:sessions[image['source_session_filename_key']].append(image)
 names=sorted(sessions);n=min(3,len(names));indices=[round(i*(len(names)-1)/(n-1))for i in range(n)]if n>1 else[0]
 selected=[]
 for i in indices:
  candidates=sorted(sessions[names[i]],key=lambda r:r['file_name']);selected.append(candidates[len(candidates)//2])
 for row in sorted(images,key=lambda r:r['file_name']):
  if len(selected)==3:break
  if row['archive_member']not in{x['archive_member']for x in selected}:selected.append(row)
 assert len(selected)==3;return sorted(selected,key=lambda r:r['file_name'])

images=[]
for k,identity in enumerate(future):
 dates=sorted(d for d,rr in byid[identity].items()if len(rr)>=3);assert len(dates)>=2
 gap=(date.fromisoformat(dates[-1])-date.fromisoformat(dates[0])).days;assert gap>=7;known=k<10
 for purpose,day in([('gallery',dates[0]),('known_query',dates[-1])]if known else[('unknown_query',dates[-1])]):
  for row in three(byid[identity][day]):images.append({**row,'purpose':purpose,'is_known':known,'day_gap':gap,'registered_gallery_date':dates[0]if known else None,'query_date':dates[-1],'local_relative_file':'input/images/'+identity+'/'+row['file_name']})
assert len(images)==len({r['archive_member']for r in images})==90
cal=[r for r in old['selected_images']if r['phase']=='calibration'];assert len(cal)==180
models=[{'name':'old_C','checkpoint_sha256':'6653555c9c806e23d2747b06db53424541254364065c53c5311b7ae2ded06b8b','features':PROJECT/'cows2021_identity_eval_20261030/delivery/results/evaluation/calibration/C_trained_seed26/all_features.npz'},
 {'name':'new_C_domain_seed26','checkpoint_sha256':'b435fb4599d307c0dd8bf3adccb42a466c271a3fdf23ab91d585d463b70cc912','features':PROJECT/'identity_domain_adapt_20261030/delivery/results/evaluation/calibration/C_domain_seed26/features.npz'}]
allrows=[];thresholds=[]
for model in models:
 with np.load(model['features'])as a:f=a['normalized'].astype(float)
 assert f.shape==(180,576)
 for fold in[0,1]:
  IDs=old['roles']['calibration_registered'][10*fold:10*(fold+1)];gi=[i for i,r in enumerate(cal)if r['purpose']=='gallery'and r['publisher_identity']in IDs];qi=[i for i,r in enumerate(cal)if r['purpose']!='gallery'and(not r['is_known']or r['publisher_identity']in IDs)];assert len(gi)==30 and len(qi)==90
  predictions=[]
  for index in qi:
   values={identity:max(float(np.dot(f[index],f[j]))for j in gi if cal[j]['publisher_identity']==identity)for identity in IDs};winner=sorted(IDs,key=lambda x:(-values[x],x))[0]
   predictions.append({'calibration_index':index,'identity':cal[index]['publisher_identity'],'is_known':cal[index]['is_known'],'predicted_ID':winner,'score':values[winner],'all_ID_scores':values})
  candidates=sorted({r['score']for r in predictions}|{float(np.nextafter(max(r['score']for r in predictions),np.inf))});options=[]
  for tau in candidates:
   c=sum(r['is_known']and r['identity']==r['predicted_ID']and r['score']>=tau for r in predictions);w=sum(r['is_known']and r['identity']!=r['predicted_ID']and r['score']>=tau for r in predictions);fa=sum(not r['is_known']and r['score']>=tau for r in predictions)
   if fa<=3:options.append((c,-w,tau,fa))
  c,nw,tau,fa=max(options);record={'model':model['name'],'fold':fold,'primary':fold==0,'registered_IDs':IDs,'threshold':tau,'C':c,'W':-nw,'U':30-c+nw,'unknown_FA':fa,'known_queries':30,'unknown_queries':60,'features_file':str(model['features']),'features_sha256':sha(model['features'])};thresholds.append(record);allrows.append({'model':model['name'],'fold':fold,'rows':predictions})
  # Independent descending sweep of saved scores checks all attainable accept sets.
  best=None
  for row in sorted(predictions,key=lambda r:r['score'],reverse=True)+[{'score':float(np.nextafter(max(x['score']for x in predictions),np.inf))}]:
   t=row['score'];accepted=[x for x in predictions if x['score']>=t];fa2=sum(not x['is_known']for x in accepted)
   if fa2>3:continue
   c2=sum(x['is_known']and x['identity']==x['predicted_ID']for x in accepted);w2=sum(x['is_known']and x['identity']!=x['predicted_ID']for x in accepted);key=(c2,-w2,t)
   if best is None or key>best:best=key
  assert best==(c,nw,tau)
save(ROOT/'results/cached_calibration_scores.json',allrows)
protocol={'status':'FINAL20_ID_METADATA_MODELS_AND_ALL10_ID_THRESHOLDS_SEALED_BEFORE_FIRST_FINAL_ID_JPEG_REQUEST','created_UTC':datetime.now(timezone.utc).isoformat(),'roles':{'registered':future[:10],'unknown':future[10:]},'source_domain_protocol_sha256':sha(PROJECT/'identity_domain_adapt_20261030/protocol/run_v1.json'),'source_test_metadata_sha256':sha(PROJECT/'cows2021_identity_intake_20261030/results/test8670_members.json'),'images':images,'image_count':90,'models':[{k:v for k,v in m.items()if k!='features'}for m in models],'score_method':'absolute_cosine_max_reference_per_ID','thresholds':thresholds,'primary_calibration_fold':0,'secondary_fold_not_selected_by_final_outcome':True,'gallery_IDs':10,'references_per_ID':3,'known_queries':30,'unknown_queries':30,'source_base_URL':old['source_base_URL'],'plan_sha256':sha(ROOT/'计划与验收.md'),'new_model_forwards':0,'new_pixels_read_or_requested':0,'identity_component_training_IDs_disjoint':True,'entire_project_pixels_unseen_claimed':False,'final12_passage_identity_GT':False,'reservedMar05toMar11_pixels_opened':False,'whole_goal_complete':False};save(ROOT/'protocol/run_v1.json',protocol)
save(ROOT/'results/pre_pixel_calibration_verification.json',{'status':'FINAL90_METADATA_ONLY4_THRESHOLDS_FROM_CACHED_FEATURES_INDEPENDENT_ACCEPT_SET_SWEEP_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(ROOT/'protocol/run_v1.json'),'thresholds':thresholds,'calibration_query_conditions':360,'new_model_forwards':0,'new_pixels_read_or_requested':0,'identity_final20_evaluation_executed':False,'whole_goal_complete':False})
print(json.dumps({'new_final_IDs':20,'registered_IDs':10,'unknown_IDs':10,'selected_image_metadata':90,'thresholds':[{k:r[k]for k in['model','fold','threshold','C','W','U','unknown_FA']}for r in thresholds],'new_pixels_read_or_requested':0,'new_model_forwards':0}))
