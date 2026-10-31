"""Independent training ledgers, geometry, matching, counters and score audit."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict,Counter
import json,hashlib,gzip,csv,math,importlib.util,sys,ast
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OUT=ROOT/'delivery/results/evaluation'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def loadgz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,obj):assert not p.exists();p.write_text(json.dumps(obj,indent=2)+'\n')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
geom=module('factor_independent_geometry',PROJECT/'detector_torso_pairs_20261029/tools/independent_geometry.py')
scanner=module('factor_independent_temporal_scanner',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py')
p=load(ROOT/'protocol/evaluation_v1.json');training=load(ROOT/'protocol/training_v4.json');freeze=load(ROOT/'delivery/results/all_checkpoints_frozen.json');s=load(OUT/'summary.json')
assert s['all_weights_freeze_sha256']==sha(ROOT/'delivery/results/all_checkpoints_frozen.json') and s['protocol_sha256']==sha(ROOT/'protocol/evaluation_v1.json')
assert len(freeze['conditions'])==15 and freeze['total_formal_optimizer_updates']==18375 and freeze['total_training_batches']==31950 and freeze['total_image_presentations']==1021350
assert s['actual_detector_source_image_forwards']==s['predictor_hook_image_forwards']==63375
assert sum(ast.literal_eval(k)[0]*v for k,v in s['predictor_tensor_shapes'].items())==63375
steps=epochs=turns=0;trainrows=[]
for condition in freeze['conditions']:
    c=condition['condition'];folder=ROOT/'delivery/results/training'/c['condition_id'];assert condition==load(folder/'completion_recovered.json')
    initial=load(folder/'initial_state.json');assert initial['initial_state_digest']==training['expected_initial_state_digests'][str(c['seed'])]
    assert sha(folder/'weights/last.pt')==condition['last_checkpoint_sha256'] and sha(folder/'weights/best.pt')==condition['archived_best_sha256']
    history=load(folder/'observed_history.json');rows=list(csv.DictReader((folder/'results.csv').open()));assert len(rows)==len(history)==10
    assert [r['training_batches'] for r in history]==list(range(213,2131,213)) and history[-1]['optimizer_steps']==1225
    schedule=load(folder/'optimizer_step_batch_indices.json');assert len(schedule)==1225 and schedule==sorted(set(schedule)) and schedule[-1]==2130
    expected=[];last=-1
    for batch in range(2130):
        accumulate=max(1,round(1+min(batch/639,1)))
        if batch-last>=accumulate:expected.append(batch+1);last=batch
    assert schedule==expected
    actualrot=load(folder/'reconstructed_rotation_schedule.json');counts=Counter()
    if c['right_angle']:
        assert len(actualrot)==2130
        for i,row in enumerate(actualrot):
            assert row['training_batch']==i+1 and len(row['turns'])==(25 if i%213==212 else 32) and all(v in [0,1,2,3] for v in row['turns']);counts.update(row['turns'])
        assert sum(counts.values())==68090 and {str(k):v for k,v in counts.items()}==condition['reconstructed_rotation_counts'];turns+=68090
    else:assert actualrot==[] and condition['reconstructed_rotation_counts']=={}
    assert condition['per_update_gradient_audit_array_recovered'] is False and condition['actual_rotation_label_row_count_recovered'] is False
    for row in rows:assert all(math.isfinite(float(v)) for v in row.values())
    epochs+=10;steps+=1225;trainrows.append({'condition':c['condition_id'],'input_size':c['imgsz'],'rotate':c['right_angle'],'seed':c['seed'],
       'epochs':10,'optimizer_steps':1225,'last_checkpoint_sha256':condition['last_checkpoint_sha256'],
       'rotation_schedule_reconstructed_not_observed':True,'per_update_gradient_audit_recovered':False,**condition['last_epoch_validation']})
assert epochs==150 and steps==18375 and turns==9*68090
images={r['file_name']:r for r in load(ROOT/'input/validation_images.json')};assert len(images)==1571
refs={name:[geom.envelope(geom.intersection(geom.corners(r['bbox_xywh_angle_rad']),[0,0,1280,720])) for r in row['reference_annotations']] for name,row in images.items()}
boxes=centers=ticks=paths=scores=validationcases=IoUs=0;maximum_inverse=0.;metrics=[]
def inverse(predictions,height,rotate):
    global boxes,maximum_inverse
    for r in predictions:
        x1,y1,x2,y2=r['network_oriented_xyxy'];expected=[y1,height-x2,y2,height-x1] if rotate else [x1,y1,x2,y2]
        delta=max(abs(a-b) for a,b in zip(expected,r['xyxy']));assert delta<1e-8 and .2-1e-7<=r['confidence']<=1
        maximum_inverse=max(maximum_inverse,delta);boxes+=1
def event_optimum(reference,predictions):
    best=(-1,float('inf'));solutions=[]
    def search(i,used,pairs,total):
        nonlocal best,solutions
        if i==len(reference):
            count=len(pairs)
            if count>best[0] or count==best[0] and total<best[1]-1e-10:best=(count,total);solutions=[pairs]
            elif count==best[0] and abs(total-best[1])<1e-10:solutions.append(pairs)
            return
        search(i+1,used,pairs,total)
        for j,pred in enumerate(predictions):
            error=abs(pred['time_s']-reference[i]['time_s'])
            if j not in used and error<=2:search(i+1,used|{j},pairs+[(i,j)],total+error)
    search(0,set(),[],0.);return best,solutions
for condition in p['new_conditions']:
    name=condition['condition'];rows=loadgz(OUT/(name+'_validation_predictions.json.gz'));assert len(rows)==1571;tp=nr=npred=0
    for row in rows:
        reference=refs[row['file_name']];assert row['source_sha256']==images[row['file_name']]['sha256'];inverse(row['predictions'],720,True)
        assert len(reference)==len(row['reference_AABB']) and max(max(abs(a-b) for a,b in zip(x,y)) for x,y in zip(reference,row['reference_AABB']))<1e-8
        matrix=[[geom.iou(a,b['xyxy']) for b in row['predictions']] for a in reference];opt,_=geom.independent_best_matching(matrix)
        assert len(row['matches'])==opt[0] and abs(sum(m['IoU'] for m in row['matches'])-opt[1])<1e-8
        tp+=opt[0];nr+=len(reference);npred+=len(row['predictions']);validationcases+=1;IoUs+=sum(len(v) for v in matrix)
    validation=next(v for v in s['validation_metrics'] if v['condition']==name)
    assert [validation[k] for k in ['references','matched','unmatched_reference','unmatched_prediction']]==[nr,tp,nr-tp,npred-tp] and validation['recall']==tp/nr
    for video in p['videos']:
        folder=OUT/video['name']/name;raw=loadgz(folder/'raw_predictions.json.gz')
        assert [r['frame0'] for r in raw]==list(range(0,video['decode_end_exclusive'],video['inference_stride']))
        for row in raw:assert row['time_s']==row['frame0']/video['fps'];inverse(row['predictions'],video['height'],video['orientation']=='clockwise90')
        for stride in video['counter_replay_strides']:
            trace=loadgz(folder/('stride'+str(stride)+'_counter_trace.json.gz'));obs=trace['observations'];ticks+=len(obs)
            assert [r['frame0'] for r in obs]==list(range(0,video['decode_end_exclusive'],stride));post=defaultdict(list)
            for row in trace['post_tracker']:post[row['frame0']].append(row)
            for row in obs:
                expected={};ids=set();assert row['time_s']==row['frame0']/video['fps']
                for r in post[row['frame0']]:
                    tid=r['track_id']
                    if tid is None:continue
                    ids.add(tid);a,b,c,d=r['xyxy'];x=(a+c)/(2*video['width']);y=(b+d)/(2*video['height'])
                    perpendicular=x if video['axis']=='y' else y;axis=y if video['axis']=='y' else x
                    if video['perpendicular_ROI'][0]<perpendicular<video['perpendicular_ROI'][1]:expected[str(tid)]=axis;centers+=1
                assert row['confirmed_positions']==expected and row['confirmed_IDs']==sorted(ids)
            saved=load(folder/('stride'+str(stride)+'_summary.json'))
            for kind,admit in [('confirmed_only_events',False),('handoff_events',True)]:
                independent,accepted=scanner.batch_events(obs,admit);assert independent==trace[kind];paths+=1
                if admit:assert sorted(accepted,key=lambda x:(x['confirmation_time_s'],x['track_id']))==sorted([a for r in obs for a in r['accepted_history']],key=lambda x:(x['confirmation_time_s'],x['track_id']))
                events=[e for e in independent if video['scope_start_frame0']<=e['frame0']<video['scope_end_exclusive']];row=next(r for r in saved if r['counter']==kind)
                assert row['events']==events and row['down']==sum(e['direction']=='A->B' for e in events) and row['up']==sum(e['direction']=='B->A' for e in events)
                if video['name']=='original':assert row['human_down_total']==12 and row['absolute_down_total_error']==abs(row['down']-12) and row['formal_event_metrics'] is None
                else:
                    best,solutions=event_optimum(video['reference_events'],events);score=row['formal_event_metrics'];pairs=sorted((m['reference_index'],m['prediction_index']) for m in score['pairs'])
                    assert score['temporally_matched']==best[0] and any(pairs==s for s in solutions)
                    correct=sum(video['reference_events'][i]['direction']==events[j]['direction'] for i,j in pairs)
                    assert [score[k] for k in ['TP','FP','FN']]==[correct,len(events)-correct,6-correct];scores+=1
                assert row==next(r for r in s['video_metrics'] if all(r[k]==row[k] for k in ['scene','condition','sample_stride','counter']));metrics.append(row)
assert validationcases==23565 and ticks==41010 and paths==90 and scores==60
gate=load(OUT/'cached_control_regression_gate.json');assert len(gate['traces'])==18 and gate['tracker_updates']==16404 and gate['counter_paths']==36 and gate['new_model_forwards_at_gate']==0
result={'status':'15_TRAINING_LEDGERS23565_VALIDATION_ASSIGNMENTS90_COUNTER_PATHS_AND60_EVENT_SCORES_INDEPENDENTLY_VERIFIED',
 'created_host_UTC':datetime.now(timezone.utc).isoformat(),'formal_conditions':15,'epochs_completed':150,'formal_optimizer_updates':steps,
 'observed_training_batches':31950,'training_image_presentations':1021350,'reconstructed_rotation_image_draws':turns,
 'per_update_gradient_arrays_recovered':False,'rotation_schedules_are_reconstructed_not_observed':True,
 'validation_image_conditions':validationcases,'candidate_validation_IoUs':IoUs,'raw_box_inverse_checks':boxes,'maximum_inverse_error':maximum_inverse,
 'native_ROI_centers_verified':centers,'tracker_observation_ticks':ticks,'independent_counter_paths':paths,'publisher6_event_score_conditions':scores,
 'cached_control_regression_counter_paths':36,'actual_network_image_forwards_supported':63375,'global_candidate_adopted':False,
 'new_independent_test':False,'new15_weights_joint_PYNQ5FPS_proven':False,'whole_goal_complete':False}
save(ROOT/'results/independent_verification.json',result)
for name,values in [('training_metrics',trainrows),('validation_metrics',s['validation_metrics']),('video_metrics',
 [{k:v for k,v in r.items() if k not in ['events','formal_event_metrics']}|({'TP':r['formal_event_metrics']['TP'],'FP':r['formal_event_metrics']['FP'],'FN':r['formal_event_metrics']['FN']} if r['formal_event_metrics'] else {'TP':None,'FP':None,'FN':None}) for r in metrics])]:
    with (ROOT/'results'/(name+'.csv')).open('x',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(values[0]));w.writeheader();w.writerows(values)
print(json.dumps(result))
