from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,math
import numpy as np

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
SOURCE=PROJECT/'identity_domain_adapt_20261030'


def load(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
 assert not path.exists();path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')


names=['original_C']+[row['name']for row in load(SOURCE/'protocol/run_v1.json')['conditions']]
methods=['absolute_cosine','different_ID_margin','distance_ratio_confidence']
specs=[]
for name in names:
 if name=='original_C':
  folder=PROJECT/'cows2021_identity_eval_20261030/delivery/results/evaluation'
  calibration=folder/'calibration/C_trained_seed26/retrieval.json'
  dev={'fold0':PROJECT/'cows2021_identity_gallery_control_20261030/results/decisions.json',
       'fold1':PROJECT/'cows2021_identity_gallery_control_20261030/results/decisions.json',
       'full40':folder/'evaluation/C_trained_seed26/retrieval_unthresholded.json',
       'retention':PROJECT/'identity_training_20261026/delivery/results/study/C_letterbox_trained_seed26/evaluation_predictions.json'}
 else:
  folder=SOURCE/'delivery/results/evaluation';calibration=folder/'calibration'/name/'retrieval.json'
  dev={scope:folder/'development'/name/(scope+'_unthresholded.json')for scope in['fold0','fold1','full40']}
  dev['retention']=folder/'retention'/name/'original_threshold_decisions.json'
 specs.append({'model':name,'calibration_file':str(calibration.resolve()),'calibration_sha256':sha(calibration),
               'development_files':{key:{'file':str(path.resolve()),'sha256':sha(path)}for key,path in dev.items()}})
# Old MultiCam rows do not persist all class scores. Recover those6ID scores from the preserved embeddings.
old_ret=PROJECT/'identity_training_20261026/delivery/results/study/C_letterbox_trained_seed26/evaluation_embeddings.npz'
protocol={'status':'FROZEN_BEFORE_ANY_NEW_REJECTION_SCORE_CALIBRATION_OR_DEVELOPMENT_DECISION',
          'created_UTC':datetime.now(timezone.utc).isoformat(),'models':specs,'methods':methods,'primary_model':'C_domain_seed26',
          'primary_method_choice':'max_calibration_C,min_calibration_W,then_method_order_absolute_margin_ratio',
          'calibration_unknown_maximum_FA':3,'calibration_unknown_queries':60,'same_prediction_ranking':True,
          'old_retention_features_file':str(old_ret.resolve()),'old_retention_features_sha256':sha(old_ret),
          'source_domain_final_review_sha256':sha(SOURCE/'results/final_review.json'),
          'plan_sha256':sha(ROOT/'计划与验收.md'),'new_model_forwards':0,'new_training_updates':0,
          'future20_ID_pixels_opened':False,'whole_goal_complete':False}
save(ROOT/'protocol/run_v1.json',protocol)


def standardize(rows):
 converted=[]
 for index,row in enumerate(rows):
  scores=row.get('scores_by_ID',row.get('all_registered_identity_scores',row.get('all_scores')))
  assert scores is not None
  ordered=sorted(scores,key=lambda key:(-scores[key],key));s1,s2=[float(scores[key])for key in ordered[:2]]
  assert ordered[0]==row['predicted_id']
  converted.append({**row,'query_key':str(row.get('source_index',row.get('evaluation_source_index',row.get('relative_path',index)))),
                    'scores_by_ID':scores,'top1_ID':ordered[0],'top2_ID':ordered[1],'s1':s1,'s2':s2})
 return converted


def confidence(row,method):
 a,b=row['s1'],row['s2']
 if method=='absolute_cosine':return a
 if method=='different_ID_margin':return a-b
 d1=math.sqrt(max(0.,2.-2.*min(1.,max(-1.,a))));d2=math.sqrt(max(0.,2.-2.*min(1.,max(-1.,b))))
 return 1.-d1/d2 if d2>1e-12 else 0.


def counts(rows):
 k=[row for row in rows if row['is_known']];u=[row for row in rows if not row['is_known']]
 result={'known_queries':len(k),'unknown_queries':len(u),
         'C':sum(row['accepted']and row['predicted_id']==row['identity']for row in k),
         'W':sum(row['accepted']and row['predicted_id']!=row['identity']for row in k),
         'U':sum(not row['accepted']for row in k),'unknown_FA':sum(row['accepted']for row in u),
         'closed_Top1':sum(row['predicted_id']==row['identity']for row in k)}
 assert result['C']+result['W']+result['U']==len(k)
 return result


calibrated=[];calrows_by_model={}
for model in specs:
 rows=standardize(load(Path(model['calibration_file'])));calrows_by_model[model['model']]=rows
 for method in methods:
  values=[confidence(row,method)for row in rows]
  candidates=sorted(set(values)|{float(np.nextafter(max(values),np.inf))});options=[]
  for tau in candidates:
   predicted=[{**row,'confidence':value,'accepted':value>=tau}for row,value in zip(rows,values)];m=counts(predicted)
   if m['unknown_FA']<=3:options.append((m['C'],-m['W'],tau,m))
  chosen=max(options,key=lambda row:row[:3]);calibrated.append({'model':model['model'],'method':method,'threshold':chosen[2],'calibration_counts':chosen[3]})
primary=max([row for row in calibrated if row['model']=='C_domain_seed26'],key=lambda row:(row['calibration_counts']['C'],-row['calibration_counts']['W'],-methods.index(row['method'])))
frozen={'status':'ALL21_REJECTION_THRESHOLDS_AND_PRIMARY_METHOD_FROZEN_BEFORE_NEW_DEVELOPMENT_DECISIONS',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'thresholds':calibrated,'primary':primary,
        'calibration_only_selection':True,'new_model_forwards':0,'whole_goal_complete':False}
save(ROOT/'results/all_methods_calibration_freeze.json',frozen)
conditions=[];decisions=[]
for spec in specs:
 for scope,binding in spec['development_files'].items():
  assert sha(Path(binding['file']))==binding['sha256']
  rows=load(Path(binding['file']))
  if spec['model']=='original_C'and scope in['fold0','fold1']:
   rows=next(group['rows']for group in rows if group['model']=='C_trained_seed26'and group['gallery_IDs']==20 and group['fold']==int(scope[-1])and group['threshold_policy']=='Cows2021_calibrated')
  elif spec['model']=='original_C'and scope=='retention':
   with np.load(old_ret)as data:gallery=data['gallery'].astype(float);query=data['query'].astype(float)
   galleryIDs=sorted({row['predicted_id']for row in rows}|{row['identity']for row in rows if row['is_known']})
   # Frozen old manifest order provides the per-reference identity labels.
   audit=load(PROJECT/'identity_training_20261026/delivery/results/input_audit/manifest.json')
   galleryrows=[row for row in audit if row['split']=='evaluation_gallery']
   assert len(galleryrows)==len(gallery)==30 and len(rows)==len(query)==60
   raw_scores=query@gallery.T
   enriched=[]
   for index,row in enumerate(rows):
    scores={ID:float(np.max(raw_scores[index,[i for i,r in enumerate(galleryrows)if r['identity']==ID]]))for ID in galleryIDs}
    assert abs(scores[row['predicted_id']]-row['similarity'])<1e-12
    enriched.append({**row,'scores_by_ID':scores})
   rows=enriched
  standard=standardize(rows)
  for method in methods:
   threshold=next(row['threshold']for row in calibrated if row['model']==spec['model']and row['method']==method)
   values=[confidence(row,method)for row in standard]
   outcome=[{**row,'confidence':value,'accepted':value>=threshold}for row,value in zip(standard,values)]
   metric=counts(outcome)
   conditions.append({'model':spec['model'],'scope':scope,'method':method,'threshold':threshold,**metric})
   decisions.append({'model':spec['model'],'scope':scope,'method':method,'threshold':threshold,'rows':outcome})
assert len(conditions)==84 and sum(len(row['rows'])for row in decisions)==13860
summary={'status':'SEVEN_FIXED_ENCODERS_THREE_REJECTION_SCORES84_CONDITIONS13860_DEVELOPMENT_DECISIONS_COMPLETE',
         'created_UTC':datetime.now(timezone.utc).isoformat(),'conditions':conditions,'primary_method_selected_on_calibration':primary,
         'new_model_forwards':0,'new_training_updates':0,'future20_ID_pixels_opened':False,'whole_goal_complete':False}
save(ROOT/'results/summary.json',summary);save(ROOT/'results/all_decisions.json',decisions)
print(json.dumps({key:value for key,value in summary.items()if key!='conditions'}))
for row in conditions:
 if row['model']=='C_domain_seed26':print(json.dumps(row))
