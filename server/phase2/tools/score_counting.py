from pathlib import Path
from collections import defaultdict
import os,csv,json,numpy as np
from scipy.optimize import linear_sum_assignment
from event_metrics import evaluate_events

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026');PH=ROOT/'phase2';OUT=PH/'results/evaluation';OUT.mkdir(parents=True,exist_ok=True)
external=json.loads((PH/'results/external_counting/all_summaries.json').read_text());gt=json.loads((PH/'results/author_gt_audit/summary.json').read_text());ref=gt['events'];result=[]
raw=np.loadtxt(PH/'data/mendeley_counting/extracted/Ground Truth/gt.txt',delimiter=',',ndmin=2)
byframe=defaultdict(list)
for r in raw:byframe[int(r[0])].append(r)
def overlap(gtboxes,predboxes):
 if not len(gtboxes) or not len(predboxes):return np.zeros((len(gtboxes),len(predboxes)))
 a=np.asarray(gtboxes);b=np.asarray(predboxes);lt=np.maximum(a[:,None,:2],b[None,:,:2]);rb=np.minimum(a[:,None,2:],b[None,:,2:]);inter=np.maximum(rb-lt,0).prod(2);area1=np.maximum(a[:,2:]-a[:,:2],0).prod(1);area2=np.maximum(b[:,2:]-b[:,:2],0).prod(1)
 return inter/np.maximum(area1[:,None]+area2[None,:]-inter,1e-12)
for row in external:
 if row['video']!='Toros':continue
 model=row['model'];sc=evaluate_events(ref,row['events'],2.);pf=defaultdict(list)
 path=PH/'results/external_counting'/model/'Toros/detections.csv'
 for r in csv.DictReader(path.open()):pf[int(r['frame'])].append(r)
 tp=fp=fn=0;track_changes=[];last={}
 for frame in range(479):
  gs=byframe[frame];ps=pf[frame]
  boxes_g=[[max(0,r[2]),max(0,r[3]),min(1920,r[2]+r[4]),min(1080,r[3]+r[5])] for r in gs]
  boxes_p=[[float(r[k]) for k in ['x1','y1','x2','y2']] for r in ps];ious=overlap(boxes_g,boxes_p);matches=[]
  if ious.size:
   cost=np.where(ious>=.5,1-ious,100000)
   ii,jj=linear_sum_assignment(cost)
   matches=[(int(i),int(j)) for i,j in zip(ii,jj) if ious[i,j]>=.5]
  tp+=len(matches);fp+=len(ps)-len(matches);fn+=len(gs)-len(matches)
  for i,j in matches:
   gid=int(gs[i][1]);pid=ps[j]['track_id']
   if pid and gid in last and frame-last[gid][0]<=30 and pid!=last[gid][1]:track_changes.append({'gt_id':gid,'frame':frame,'old_prediction_id':last[gid][1],'new_prediction_id':pid})
   if pid:last[gid]=(frame,pid)
 detector={'reference_boxes':len(raw),'matched_iou50':tp,'false_prediction_boxes':fp,'unmatched_reference_boxes':fn,'precision_at_iou50':tp/(tp+fp) if tp+fp else None,'recall_at_iou50':tp/(tp+fn) if tp+fn else None,'scope':'Per-frame diagnostic against published boxes clipped to image; publisher annotation defects/edge fragments retained; not AP/mAP/IDF1','diagnostic_matched_id_changes':len(track_changes),'changes':track_changes}
 result.append({'model':model,'weights_sha256':row['model_sha256'],'video':'Toros','reference_authority':'publisher manually corrected trajectories; event labels derived using declared complete-crossing definition','event_metrics':sc,'box_diagnostics':detector})

draft_ref=list(csv.DictReader((PH/'annotations/multicam_source_events_v1.csv').open()))
draft=[{'time_s':(float(r['start_s'])+float(r['end_s']))/2,'direction':r['direction'],'reference_id':r['reference_id'],'interval_s':[float(r['start_s']),float(r['end_s'])]} for r in draft_ref]
draft_scope=json.loads((PH/'annotations/multicam_review_scope.json').read_text());draft_rows=[]
for model,path in [('generic',ROOT/'results/multicam_count_dev/predicted_events.csv'),('pilot',ROOT/'results/multicam_count_finetuned_dev/predicted_events.csv')]:
 preds=list(csv.DictReader(path.open()));keep=[];ignored=[]
 for r in preds:
  p={'time_s':float(r['time_s']),'direction':r['direction'],'track_id':int(r['track_id'])}
  if any(x['start_s']<=p['time_s']<=x['end_s'] for x in draft_scope['ignore_intervals']):ignored.append(p)
  else:keep.append(p)
 sc=evaluate_events(draft,keep,2.)
 draft_rows.append({'model':model,'metrics':sc,'ignored_predictions':ignored,'reference_status':'produced_not_user_validated','blinding':draft_scope['blinding'],'metric_scope':'Five isolated reviewed source events only; crowded interval ignored. No full-video accuracy, blinded or publication-level claim.'})

summary={'job_id':os.environ['SLURM_JOB_ID'],'frozen_external_results':result,'source_draft_results':draft_rows,'external_direction_coverage':[{'video':r['video'],'model':r['model'],'A_to_B':r['A_to_B'],'B_to_A':r['B_to_A'],'processed_frames':r['processed_frames']} for r in external],'publication_readiness':'External sample results are small and not simultaneous two-way farm validation; source draft still needs human validation; no FPGA deployment performance'}
(OUT/'metrics.json').write_text(json.dumps(summary,indent=2))
flat=[]
for r in result:
 m=r['event_metrics'];flat.append({'model':r['model'],'video':r['video'],**{k:m[k] for k in ['reference_events','predicted_events','TP','FP','FN','precision','recall','f1','wrong_direction_matches','mean_absolute_direction_count_error']}})
with (OUT/'external_event_metrics.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
print(json.dumps(summary),flush=True)
