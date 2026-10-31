"""Separate geometry, brute-force matching and temporal-run event recomputation."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json,gzip,hashlib,importlib.util,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OUT=ROOT/'delivery/results/quality_v2'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def gz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
geo=module('independent_quality_geometry',PROJECT/'detector_torso_pairs_20261029/tools/independent_geometry.py')
scanner=module('independent_quality_runs',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py')
p=load(ROOT/'protocol/eval_v2.json');s=load(OUT/'summary.json')
assert s['protocol_sha256']==sha(ROOT/'protocol/eval_v2.json') and s['ORT_actual_forwards']=={'FP32':4225,'QDQ':4225} and s['native_integer_actual_forwards']==8
images={r['file_name']:r for r in load(ROOT/'input/validation_images.json')}
matching_problems=refboxes=valboxes=0;max_geometry=0.;metrics=[]
with np.load(OUT/'validation_all_raw.npz') as arrays:
 for mode in ['FP32','QDQ']:
  records=gz(OUT/(mode+'_validation_predictions.json.gz'));actual=arrays[mode]
  assert len(records)==1571 and actual.shape==(1571,300,6) and np.isfinite(actual).all() and np.all(actual[:,:,5]==0)
  tp=n=gt=0
  for record,raw in zip(records,actual):
   image=images[record['file_name']];assert record['source_sha256']==image['sha256']
   references=[geo.envelope(geo.intersection(geo.corners(r['bbox_xywh_angle_rad']),[0,0,1280,720])) for r in image['reference_annotations']]
   assert len(references)==len(record['reference_AABB'])
   for before,after in zip(references,record['reference_AABB']):
    error=max(abs(a-b) for a,b in zip(before,after));assert error<1e-8;max_geometry=max(max_geometry,error);refboxes+=1
   predictions=record['predictions'];assert len(predictions)==int((raw[:,4]>=.2).sum())
   matrix=[[geo.iou(a,b['xyxy']) for b in predictions] for a in references]
   best,winners=geo.independent_best_matching(matrix,.5);chosen=record['matches']
   assert len(chosen)==best[0] and len({r['prediction_index'] for r in chosen})==len(chosen)
   assert abs(sum(r['IoU'] for r in chosen)-best[1])<1e-8
   for r in chosen:assert abs(r['IoU']-matrix[r['reference_index']][r['prediction_index']])<1e-8
   matching_problems+=1;tp+=len(chosen);gt+=len(references);n+=len(predictions);valboxes+=len(predictions)
  row=next(x for x in s['validation_metrics'] if x['mode']==mode)
  assert [row[k] for k in ['TP','unmatched_reference','unmatched_prediction']]==[tp,gt-tp,n-tp]
  assert row['recall']==tp/gt and row['precision_vs_reference']==tp/n
  metrics.append(row)
def event_optimum(reference,predictions):
 best=(-1,float('inf'));winners=[]
 def search(i,used,pairs,cost):
  nonlocal best,winners
  if i==len(reference):
   candidate=(len(pairs),cost)
   if candidate[0]>best[0] or candidate[0]==best[0] and cost<best[1]-1e-10:best=candidate;winners=[pairs]
   elif candidate[0]==best[0] and abs(cost-best[1])<1e-10:winners.append(pairs)
   return
  search(i+1,used,pairs,cost)
  for j,event in enumerate(predictions):
   error=abs(event['time_s']-reference[i]['time_s'])
   if j not in used and error<=2:search(i+1,used|{j},pairs+[(i,j)],cost+error)
 search(0,set(),[],0.);return best,winners
rawticks=boxes=ticks=paths=formal=0;maximum_inverse=0.;table=[]
for video in p['videos']:
 x0,y0,x1,y1=video['detection_crop_xyxy'];height=y1-y0;rotate=video['orientation']=='clockwise90'
 inverse=np.array([[0,1,x0],[-1,0,y1],[0,0,1]],float) if rotate else np.array([[1,0,x0],[0,1,y0],[0,0,1]],float)
 with np.load(OUT/(video['name']+'_all_raw.npz')) as arrays:
  for mode in ['FP32','QDQ']:
   folder=OUT/video['name']/mode;records=gz(folder/'raw_predictions.json.gz');networkraw=arrays[mode]
   assert networkraw.shape==(len(records),300,6) and np.isfinite(networkraw).all() and np.all(networkraw[:,:,5]==0)
   assert [r['frame0'] for r in records]==list(range(0,video['decode_end_exclusive'],video['inference_stride']))
   rawticks+=len(records)
   for row,raw in zip(records,networkraw):
    assert row['time_s']==row['frame0']/video['fps'] and len(row['predictions'])==int((raw[:,4]>=.2).sum())
    for r,selected in zip(row['predictions'],raw[raw[:,4]>=.2]):
     assert r['confidence']==float(selected[4]) and r['class']==0
     a,b,c,d=r['crop_oriented_xyxy'];corners=np.array([[a,b,1],[c,b,1],[c,d,1],[a,d,1]])@inverse.T
     expected=[*corners[:,:2].min(0),*corners[:,:2].max(0)]
     error=max(abs(a-b) for a,b in zip(expected,r['xyxy']));maximum_inverse=max(maximum_inverse,error);assert error<1e-8
     boxes+=1
   for stride in video['counter_replay_strides']:
    trace=gz(folder/('stride'+str(stride)+'_counter_trace.json.gz'));obs=trace['observations']
    assert [r['frame0'] for r in obs]==list(range(0,video['decode_end_exclusive'],stride));ticks+=len(obs)
    byframe=defaultdict(list)
    for row in trace['post_tracker']:byframe[row['frame0']].append(row)
    for row in obs:
     expected={};active=set()
     for box in byframe[row['frame0']]:
      if box['track_id'] is None:continue
      tid=box['track_id'];active.add(tid);a,b,c,d=box['xyxy'];cx=(a+c)/(2*video['width']);cy=(b+d)/(2*video['height'])
      if video['perpendicular_ROI'][0]<(cx if video['axis']=='y' else cy)<video['perpendicular_ROI'][1]:expected[str(tid)]=cy if video['axis']=='y' else cx
     assert row['confirmed_positions']==expected and row['confirmed_IDs']==sorted(active)
    for kind,admit in [('confirmed_only_events',False),('handoff_events',True)]:
     events,accepted=scanner.batch_events(obs,admit);assert events==trace[kind];paths+=1
     events=[e for e in events if video['scope_start_frame0']<=e['frame0']<video['scope_end_exclusive']]
     metric=next(x for x in s['video_metrics'] if x['scene']==video['name'] and x['mode']==mode and x['stride']==stride and x['counter']==kind)
     assert metric['events']==events and metric['down']==sum(e['direction']=='A->B' for e in events) and metric['up']==sum(e['direction']=='B->A' for e in events)
     if video['name']=='toros':
      best,winners=event_optimum(video['reference_events'],events);score=metric['formal_event_metrics'];selected=sorted((r['reference_index'],r['prediction_index']) for r in score['pairs'])
      assert selected in winners and score['temporally_matched']==best[0]
      correct=sum(video['reference_events'][a]['direction']==events[b]['direction'] for a,b in selected)
      assert [score[k] for k in ['TP','FP','FN']]==[correct,len(events)-correct,6-correct];formal+=1
     else:assert metric['formal_event_metrics'] is None
     table.append({k:metric[k] for k in ['scene','mode','stride','counter','down','up']})
assert matching_problems==3142 and refboxes==3728 and rawticks==5308 and ticks==5468 and paths==12 and formal==8
anchors=load(OUT/'native_integer_anchors.json');assert len(anchors)==8
for row in anchors:
 with np.load(OUT/row['file']) as ar:
  assert hashlib.sha256(ar['input'].tobytes()).hexdigest()==row['input_tensor_sha256']
  assert hashlib.sha256(ar['native_integer_raw'].tobytes()).hexdigest()==row['native_integer_raw_sha256']
  expected=PROJECT/'factorial_lane_crop_20261029/delivery/results/roi/pixel_controls'/(row['scene']+'_f'+str(row['frame0'])+'_s192_NN.npz')
  with np.load(expected) as old:assert ar['input'][0].tobytes()==old['actual_input'].tobytes()
record={'status':'3142_VALIDATION_MATCHES_AND12_VIDEO_COUNTER_PATHS_INDEPENDENTLY_RECOMPUTED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'validation_matching_problems':matching_problems,'validation_reference_boxes':refboxes,
 'validation_predicted_boxes':valboxes,'maximum_independent_reference_geometry_error':max_geometry,
 'raw_video_ticks':rawticks,'raw_video_boxes_inverse_checked':boxes,'maximum_inverse_error':maximum_inverse,
 'counter_ticks':ticks,'counter_paths':paths,'publisher_event_score_conditions':formal,'native_integer_input_anchor_bytes_checked':8,
 'validation_metrics':metrics,'video_counts':table,'failed_v1_preserved':True,'whole_goal_complete':False,'new_network_forwards':0}
file=ROOT/'results/independent_quality_verification.json';assert not file.exists();file.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
