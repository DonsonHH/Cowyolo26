from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json,hashlib,gzip,math,importlib.util,sys,csv
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OUT=ROOT/'delivery/results/baseline'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def loadgz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists(),p;p.write_text(json.dumps(v,indent=2)+'\n')
def module(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
geometry=module('independent_pair_geometry',PROJECT/'detector_torso_pairs_20261029/tools/independent_geometry.py')
scanner=module('independent_lowres_temporal_scanner',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py')
protocol=load(ROOT/'protocol/baseline_v2_path_fix.json');summary=load(OUT/'summary.json');assert summary['protocol_sha256']==sha(ROOT/'protocol/baseline_v2_path_fix.json')
assert summary['actual_detector_source_image_forwards']==50700
assert summary['resumed_new_detector_source_image_forwards']==summary['predictor_inference_image_hook_count_current_resume']==5748
assert summary['prior_completed_source_prediction_records']==44952 and summary['prior_in_memory_predictor_hook_counter_not_recovered_after_failure'] is True
assert summary['tracker_updates']==32808 and summary['counter_paths']==72
gate=load(OUT/'baseline_counter_regression.json');assert len(gate)==2 and all(r['all_observations_and_both_event_lists_exact'] for r in gate)
imageindex={r['file_name']:r for r in load(ROOT/'input/validation_images.json')}
fullref={}
for name,image in imageindex.items():
    fullref[name]=[geometry.envelope(geometry.intersection(geometry.corners(r['bbox_xywh_angle_rad']),[0,0,1280,720])) for r in image['reference_annotations']]
validation_rows=[];candidate_ious=0;validation_matches=0;inverse_count=0;max_inverse_error=0.;video_summary=[];post_centers=0;all_ticks=0;event_paths=0;formal_scores=0;ambiguous_event_optima=0
def check_inverse(predictions,height,rotate):
    global inverse_count,max_inverse_error
    for r in predictions:
        x1,y1,x2,y2=r['network_oriented_xyxy'];expected=[y1,height-x2,y2,height-x1] if rotate else [x1,y1,x2,y2]
        delta=max(abs(a-b) for a,b in zip(expected,r['xyxy']));max_inverse_error=max(max_inverse_error,delta);assert delta<1e-8 and r['confidence']>=.2-1e-7
        inverse_count+=1
def event_optimum(reference,predictions,tolerance):
    n,m=len(reference),len(predictions);best=(-1,float('inf'));assignments=[]
    def search(i,used,pairs,total):
        nonlocal best,assignments
        if i==n:
            count=len(pairs)
            if count>best[0] or count==best[0] and total<best[1]-1e-10:best=(count,total);assignments=[pairs]
            elif count==best[0] and abs(total-best[1])<1e-10:assignments.append(pairs)
            return
        search(i+1,used,pairs,total)
        for j,p in enumerate(predictions):
            error=abs(p['time_s']-reference[i]['time_s'])
            if j not in used and error<=tolerance:search(i+1,used|{j},pairs+[(i,j)],total+error)
    search(0,set(),[],0.)
    return best,assignments
for condition in protocol['conditions']:
    cname=condition['condition'];rows=loadgz(OUT/(cname+'_validation_predictions.json.gz'));assert len(rows)==1571
    tp=predcount=gtcount=0
    for row in rows:
        assert row['source_sha256']==imageindex[row['file_name']]['sha256'];refs=fullref[row['file_name']]
        assert len(refs)==len(row['reference_AABB']) and max(max(abs(a-b) for a,b in zip(x,y)) for x,y in zip(refs,row['reference_AABB']))<1e-8
        check_inverse(row['predictions'],720,True)
        matrix=[[geometry.iou(a,b['xyxy']) for b in row['predictions']] for a in refs];optimum,_=geometry.independent_best_matching(matrix)
        assert len(row['matches'])==optimum[0] and abs(sum(r['IoU'] for r in row['matches'])-optimum[1])<1e-8
        assert len({r['prediction_index'] for r in row['matches']})==len(row['matches'])
        tp+=len(row['matches']);gtcount+=len(refs);predcount+=len(row['predictions']);candidate_ious+=len(refs)*len(row['predictions'])
    metric=next(r for r in summary['validation_metrics'] if r['condition']==cname)
    assert [metric[k] for k in ['references','matched','unmatched_reference','unmatched_prediction']]==[gtcount,tp,gtcount-tp,predcount-tp]
    assert metric['recall']==tp/gtcount
    validation_rows.append(metric);validation_matches+=tp
    for spec in protocol['videos']:
        folder=OUT/spec['name']/cname;raw=loadgz(folder/'raw_predictions.json.gz');assert [r['frame0'] for r in raw]==list(range(0,spec['decode_end_exclusive'],spec['inference_stride']))
        for row in raw:check_inverse(row['predictions'],spec['height'],spec['orientation']=='clockwise90')
        for stride in spec['counter_replay_strides']:
            trace=loadgz(folder/('stride'+str(stride)+'_counter_trace.json.gz'));obs=trace['observations']
            assert [r['frame0'] for r in obs]==list(range(0,spec['decode_end_exclusive'],stride));all_ticks+=len(obs)
            byframe=defaultdict(list)
            for row in trace['post_tracker']:byframe[row['frame0']].append(row)
            for r in obs:
                assert r['time_s']==r['frame0']/spec['fps'];expected={};ids=set()
                for row in byframe[r['frame0']]:
                    tid=row['track_id']
                    if tid is None:continue
                    ids.add(tid);x1,y1,x2,y2=row['xyxy'];cx=(x1+x2)/(2*spec['width']);cy=(y1+y2)/(2*spec['height'])
                    cross=cx if spec['axis']=='y' else cy;axis=cy if spec['axis']=='y' else cx
                    if spec['perpendicular_ROI'][0]<cross<spec['perpendicular_ROI'][1]:expected[str(tid)]=axis;post_centers+=1
                assert expected==r['confirmed_positions'] and sorted(ids)==r['confirmed_IDs']
            saved=load(folder/('stride'+str(stride)+'_summary.json'))
            for kind,admit in [('confirmed_only_events',False),('handoff_events',True)]:
                independent,admissions=scanner.batch_events(obs,admit);assert independent==trace[kind];event_paths+=1
                if admit:
                    actual=[a for r in obs for a in r['accepted_history']]
                    assert sorted(admissions,key=lambda x:(x['confirmation_time_s'],x['track_id']))==sorted(actual,key=lambda x:(x['confirmation_time_s'],x['track_id']))
                events=[r for r in independent if spec['scope_start_frame0']<=r['frame0']<spec['scope_end_exclusive']]
                row=next(r for r in saved if r['counter']==kind);assert row['events']==events
                assert row['down']==sum(e['direction']=='A->B' for e in events) and row['up']==sum(e['direction']=='B->A' for e in events)
                if spec['name']=='original':
                    assert row['human_down_total']==12 and row['absolute_down_total_error']==abs(row['down']-12) and row['formal_event_metrics'] is None
                else:
                    score=row['formal_event_metrics'];reference=spec['reference_events'];best,assignments=event_optimum(reference,events,2.)
                    if len(assignments)>1:ambiguous_event_optima+=1
                    assert score['temporally_matched']==best[0]
                    actualpairs=sorted((p['reference_index'],p['prediction_index']) for p in score['pairs'])
                    assert any(actualpairs==pairs for pairs in assignments)
                    correct=sum(reference[i]['direction']==events[j]['direction'] for i,j in actualpairs)
                    assert [score[k] for k in ['TP','FP','FN']]==[correct,len(events)-correct,6-correct];formal_scores+=1
                video_summary.append(row)
assert all_ticks==32808 and event_paths==72 and formal_scores==48
out={'status':'ALL12_LOWRES_VALIDATION_NATIVE_INVERSES_AND72_COUNTER_PATHS_INDEPENDENTLY_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
'protocol_sha256':sha(ROOT/'protocol/baseline_v2_path_fix.json'),'validation_images_per_condition':1571,'validation_reference_per_condition':1864,
'validation_matching_cases':1571*12,'candidate_validation_IoUs':candidate_ious,'matched_validation_reference_conditions':validation_matches,
'raw_boxes_inverse_verified':inverse_count,'maximum_native_inverse_error':max_inverse_error,'counter_observation_ticks':all_ticks,
'ROI_centers_recomputed':post_centers,'independent_counter_paths':event_paths,'publisher6_event_metric_conditions':formal_scores,
'event_matching_multiple_optima_conditions':ambiguous_event_optima,'all_seed_sizes_sampling_rates_and_negative_results_retained':True,
'new_training_updates':0,'new_independent_test':False,'PYNQ5FPS_proven':False,'whole_goal_complete':False}
save(ROOT/'results/independent_verification.json',out);save(ROOT/'results/independent_validation_table.json',validation_rows);save(ROOT/'results/independent_video_table.json',video_summary)
for name,rows in [('validation_metrics',validation_rows),('video_metrics',[{k:v for k,v in r.items() if k not in ['events','formal_event_metrics']}|
({'TP':r['formal_event_metrics']['TP'],'FP':r['formal_event_metrics']['FP'],'FN':r['formal_event_metrics']['FN']} if r['formal_event_metrics'] else {'TP':None,'FP':None,'FN':None}) for r in video_summary])]:
    with (ROOT/'results'/(name+'.csv')).open('x',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps(out))
