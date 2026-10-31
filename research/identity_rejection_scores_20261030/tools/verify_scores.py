from pathlib import Path
from datetime import datetime,timezone
import json,math
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def load(path):return json.loads(path.read_text(encoding='utf-8'))


plan=load(ROOT/'protocol/run_v1.json');freeze=load(ROOT/'results/all_methods_calibration_freeze.json');summary=load(ROOT/'results/summary.json')
assert datetime.fromisoformat(freeze['created_UTC'])<datetime.fromisoformat(summary['created_UTC'])
all_decisions=load(ROOT/'results/all_decisions.json');assert len(all_decisions)==84
methods=plan['methods'];calibration=[];checked=cells=0;intervals=[];paired=[]


def independent_confidence(scores,method):
 ordered=sorted(scores,key=lambda key:(-scores[key],key));a,b=[float(scores[key])for key in ordered[:2]]
 if method=='absolute_cosine':value=a
 elif method=='different_ID_margin':value=a-b
 else:
  squared=[2.*(1.-np.clip(number,-1.,1.))for number in[a,b]]
  value=1.-float(np.sqrt(max(0.,squared[0])/squared[1]))if squared[1]>1e-24 else 0.
 return value,ordered[:2]


def metric(rows):
 known=[row for row in rows if row['is_known']];unknown=[row for row in rows if not row['is_known']]
 return{'known_queries':len(known),'unknown_queries':len(unknown),'C':sum(row['accepted']and row['predicted_id']==row['identity']for row in known),
        'W':sum(row['accepted']and row['predicted_id']!=row['identity']for row in known),'U':sum(not row['accepted']for row in known),
        'unknown_FA':sum(row['accepted']for row in unknown),'closed_Top1':sum(row['predicted_id']==row['identity']for row in known)}


def per_identity(rows):
 values={}
 for identity in sorted({row['identity']for row in rows}):
  group=[row for row in rows if row['identity']==identity];known=group[0]['is_known'];n=len(group)
  values[identity]={'is_known':known,'C':sum(row['accepted']and row['predicted_id']==identity for row in group)/n if known else None,
                    'W':sum(row['accepted']and row['predicted_id']!=identity for row in group)/n if known else None,
                    'FA':sum(row['accepted']for row in group)/n if not known else None}
 return values


for spec in plan['models']:
 rows=load(Path(spec['calibration_file']))
 for method in methods:
  scores=[row.get('scores_by_ID',row.get('all_registered_identity_scores',row.get('all_scores')))for row in rows]
  values=[independent_confidence(score,method)[0]for score in scores]
  candidates=set(values)|{float(np.nextafter(max(values),np.inf))};valid=[]
  for tau in candidates:
   measured=metric([{**row,'accepted':value>=tau}for row,value in zip(rows,values)])
   if measured['unknown_FA']<=3:valid.append((measured['C'],-measured['W'],tau,measured))
  best=max(valid,key=lambda row:row[:3]);saved=next(row for row in freeze['thresholds']if row['model']==spec['model']and row['method']==method)
  assert abs(best[2]-saved['threshold'])<1e-14 and best[3]==saved['calibration_counts']
  calibration.append({'model':spec['model'],'method':method,'threshold':saved['threshold'],'calibration_counts':best[3]})
for group in all_decisions:
 for row in group['rows']:
  value,top2=independent_confidence(row['scores_by_ID'],group['method']);assert abs(value-row['confidence'])<1e-14
  assert top2==[row['top1_ID'],row['top2_ID']]and top2[0]==row['predicted_id']
  assert row['accepted']==(row['confidence']>=group['threshold']);checked+=1;cells+=len(row['scores_by_ID'])
 expected=next(row for row in summary['conditions']if all(row[key]==group[key]for key in['model','scope','method']))
 assert group['threshold']==next(row['threshold']for row in freeze['thresholds']if row['model']==group['model']and row['method']==group['method'])
 for key,value in metric(group['rows']).items():assert expected[key]==value
 byID=per_identity(group['rows']);rng=np.random.default_rng(26);record={}
 for field,known in[('C',True),('W',True),('FA',False)]:
  data=np.array([row[field]for row in byID.values()if row['is_known']==known]);samples=np.array([data[rng.integers(0,len(data),len(data))].mean()for _ in range(2000)])
  record[field]={'mean':float(data.mean()),'ID_clusters':len(data),'bootstrap95':np.quantile(samples,[.025,.975]).tolist()}
 intervals.append({'model':group['model'],'scope':group['scope'],'method':group['method'],'statistics':record})
 if group['method']!='absolute_cosine':
  base=next(item for item in all_decisions if item['model']==group['model']and item['scope']==group['scope']and item['method']=='absolute_cosine')
  baseline=per_identity(base['rows']);assert list(baseline)==list(byID);rng=np.random.default_rng(26);record={}
  for field,known in[('C',True),('W',True),('FA',False)]:
   delta=np.array([row[field]-baseline[identity][field]for identity,row in byID.items()if row['is_known']==known]);samples=np.array([delta[rng.integers(0,len(delta),len(delta))].mean()for _ in range(2000)])
   record[field]={'paired_mean_delta':float(delta.mean()),'ID_clusters':len(delta),'bootstrap95':np.quantile(samples,[.025,.975]).tolist()}
  paired.append({'model':group['model'],'scope':group['scope'],'method':group['method'],'statistics':record})
chosen=max([row for row in calibration if row['model']=='C_domain_seed26'],key=lambda row:(row['calibration_counts']['C'],-row['calibration_counts']['W'],-methods.index(row['method'])))
assert chosen==freeze['primary']and chosen['method']=='absolute_cosine'
assert checked==13860 and len(intervals)==84 and len(paired)==56
for filename,value in[('ID_intervals.json',intervals),('paired_to_absolute.json',paired)]:
 p=ROOT/'results'/filename;assert not p.exists();p.write_text(json.dumps(value,indent=2)+'\n')
result={'status':'ALL21_THRESHOLDS84_CONDITIONS13860_DECISIONS_AND56_ID_PAIRED_CONTRASTS_INDEPENDENTLY_VERIFIED',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'thresholds':21,'outcome_conditions':84,'decisions':checked,'ID_score_cells':cells,
        'ID_bootstrap_condition_sets':84,'paired_comparisons_to_absolute':56,'primary_calibration_method':'absolute_cosine',
        'primary_not_reselected_by_development_scores':True,'new_model_forwards':0,'new_training_updates':0,'future20_ID_pixels_opened':False,'whole_goal_complete':False}
p=ROOT/'results/independent_verification.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
