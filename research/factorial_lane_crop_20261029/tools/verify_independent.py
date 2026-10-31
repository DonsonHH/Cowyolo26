"""Independent matrix inverse, temporal-run scanner and event assignment checks."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json,hashlib,gzip,sys,importlib.util,csv,ast
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OUT=ROOT/'delivery/results/roi'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def loadgz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('independent_roi_scanner',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py')
scanner=importlib.util.module_from_spec(spec);sys.modules[spec.name]=scanner;spec.loader.exec_module(scanner)
p=load(ROOT/'protocol/crop_v1.json');s=load(OUT/'summary.json');assert s['protocol_sha256']==sha(ROOT/'protocol/crop_v1.json')
assert s['actual_detector_source_image_forwards']==s['active_predictor_inference_image_calls']==39810
assert s['new_crop_tracker_updates']==s['baseline_full_tracker_updates_replayed']==41010
assert s['new_crop_counter_paths']==s['baseline_full_cache_counter_paths_exact']==90
assert sum(ast.literal_eval(k)[0]*v for k,v in s['predictor_tensor_shape_counts'].items())==39810
prior=PROJECT/'detector_factorial_20261029/delivery/results/evaluation'
assert sha(prior/'summary.json')==p['full_input_summary_sha256']
assert sha(PROJECT/'detector_factorial_20261029/delivery/results/all_checkpoints_frozen.json')==p['all15_checkpoint_freeze_sha256']
gate=load(OUT/'full_input_cache_regression_gate.json');assert gate['new_model_forwards_at_gate']==0 and gate['tracker_updates']==41010
assert len(gate['traces'])==45 and all(x['entire_trace_exact'] for x in gate['traces']) and sum(x['observation_ticks'] for x in gate['traces'])==41010
tensorrows=load(OUT/'input_tensor_controls.json');assert len(tensorrows)==120
for row in tensorrows:
    key=row['scene']+'_f'+str(row['frame0'])+'_s'+str(row['input_size'])
    assert row['tensor_sha256']==p['expected_NN_input_hashes_24_source_frame_sizes'][key]
controls=PROJECT/'lowres_roi_20261029/delivery/results/roi/pixel_controls'
for scene in p['videos']:
    for frame in scene['pixel_control_frames']:
        for size in [192,256,320]:
            name=scene['name']+'_f'+str(frame)+'_s'+str(size)+'_NN.npz'
            with np.load(OUT/'pixel_controls'/name) as new:array=new['actual_input']
            with np.load(controls/name) as old:expected=old['actual_input']
            assert array.shape==expected.shape==(3,size,size) and array.dtype==expected.dtype==np.float32 and array.tobytes()==expected.tobytes()
def event_optimum(reference,predictions,tolerance):
    best=(-1,float('inf'));assignments=[]
    def search(i,used,pairs,total):
        nonlocal best,assignments
        if i==len(reference):
            count=len(pairs)
            if count>best[0] or count==best[0] and total<best[1]-1e-10:best=(count,total);assignments=[pairs]
            elif count==best[0] and abs(total-best[1])<1e-10:assignments.append(pairs)
            return
        search(i+1,used,pairs,total)
        for j,prediction in enumerate(predictions):
            error=abs(prediction['time_s']-reference[i]['time_s'])
            if j not in used and error<=tolerance:search(i+1,used|{j},pairs+[(i,j)],total+error)
    search(0,set(),[],0.);return best,assignments
raw_ticks=boxes=obs_ticks=centers=paths=formal=ambiguous=0;inverse_error=0.;rows=[];flat=[]
for video in p['videos']:
    x0,y0,x1,y1=video['detection_crop_xyxy'];height=y1-y0
    # Invert transformed corners with a homogeneous matrix, then form envelope.
    matrix=np.array([[0,1,x0],[-1,0,y0+height],[0,0,1]],float) if video['orientation']=='clockwise90' else np.array([[1,0,x0],[0,1,y0],[0,0,1]],float)
    for c in p['conditions']:
        folder=OUT/video['name']/c['condition'];raw=loadgz(folder/'raw_predictions.json.gz')
        assert [r['frame0'] for r in raw]==list(range(0,video['decode_end_exclusive'],video['inference_stride']));raw_ticks+=len(raw)
        for row in raw:
            assert row['time_s']==row['frame0']/video['fps']
            for r in row['predictions']:
                u0,v0,u1,v1=r['crop_oriented_xyxy'];corners=np.array([[u0,v0,1],[u1,v0,1],[u1,v1,1],[u0,v1,1]])@matrix.T
                expected=[*corners[:,:2].min(axis=0),*corners[:,:2].max(axis=0)]
                delta=max(abs(a-b) for a,b in zip(expected,r['xyxy']));inverse_error=max(inverse_error,delta)
                assert delta<1e-8 and x0-1e-4<=r['xyxy'][0]<=r['xyxy'][2]<=x1+1e-4 and y0-1e-4<=r['xyxy'][1]<=r['xyxy'][3]<=y1+1e-4
                assert .2-1e-7<=r['confidence']<=1 and r['class']==(19 if c['model']=='official' else 0);boxes+=1
        for stride in video['counter_replay_strides']:
            trace=loadgz(folder/('stride'+str(stride)+'_counter_trace.json.gz'));obs=trace['observations']
            assert [r['frame0'] for r in obs]==list(range(0,video['decode_end_exclusive'],stride));obs_ticks+=len(obs)
            byframe=defaultdict(list)
            for row in trace['post_tracker']:byframe[row['frame0']].append(row)
            for row in obs:
                assert row['time_s']==row['frame0']/video['fps'];expected={};ids=set()
                for post in byframe[row['frame0']]:
                    tid=post['track_id']
                    if tid is None:continue
                    ids.add(tid);a,b,cx,d=post['xyxy'];x=(a+cx)/(2*video['width']);y=(b+d)/(2*video['height'])
                    cross=x if video['axis']=='y' else y;axis=y if video['axis']=='y' else x
                    if video['perpendicular_ROI'][0]<cross<video['perpendicular_ROI'][1]:expected[str(tid)]=axis;centers+=1
                assert expected==row['confirmed_positions'] and sorted(ids)==row['confirmed_IDs']
            saved=load(folder/('stride'+str(stride)+'_summary.json'))
            for kind,admit in [('confirmed_only_events',False),('handoff_events',True)]:
                independent,admissions=scanner.batch_events(obs,admit);assert independent==trace[kind];paths+=1
                if admit:assert sorted(admissions,key=lambda x:(x['confirmation_time_s'],x['track_id']))==sorted([a for o in obs for a in o['accepted_history']],key=lambda x:(x['confirmation_time_s'],x['track_id']))
                events=[e for e in independent if video['scope_start_frame0']<=e['frame0']<video['scope_end_exclusive']]
                row=next(r for r in saved if r['counter']==kind);assert row['events']==events
                assert row['down']==sum(e['direction']=='A->B' for e in events) and row['up']==sum(e['direction']=='B->A' for e in events)
                if video['name']=='original':assert row['human_down_total']==12 and row['absolute_down_total_error']==abs(row['down']-12) and row['formal_event_metrics'] is None
                else:
                    score=row['formal_event_metrics'];reference=video['reference_events'];best,assignments=event_optimum(reference,events,2.)
                    if len(assignments)>1:ambiguous+=1
                    assert score['temporally_matched']==best[0]
                    actual=sorted((q['reference_index'],q['prediction_index']) for q in score['pairs']);assert any(actual==pairs for pairs in assignments)
                    correct=sum(reference[i]['direction']==events[j]['direction'] for i,j in actual)
                    assert [score[k] for k in ['TP','FP','FN']]==[correct,len(events)-correct,6-correct];formal+=1
                assert row==next(q for q in s['video_metrics'] if all(q[k]==row[k] for k in ['scene','condition','sample_stride','counter']))
                old=next(q for q in load(prior/'video_metrics.json') if all(q[k]==row[k] for k in ['scene','condition','sample_stride','counter']))
                paired=next(q for q in s['paired_full_vs_roi'] if all(q[k]==row[k] for k in ['scene','condition','sample_stride','counter']))
                assert [paired[k] for k in ['full_down','crop_down','full_up','crop_up']]==[old['down'],row['down'],old['up'],row['up']]
                assert paired['full_TP_FP_FN']==([old['formal_event_metrics'][k] for k in ['TP','FP','FN']] if old['formal_event_metrics'] else None)
                assert paired['crop_TP_FP_FN']==([row['formal_event_metrics'][k] for k in ['TP','FP','FN']] if row['formal_event_metrics'] else None)
                rows.append(row);flat.append({k:v for k,v in paired.items()}|{'model':c['model'],'human_down_reference':12 if video['name']=='original' else None})
assert raw_ticks==39810 and obs_ticks==41010 and paths==90 and formal==60
assert s['paired_full_vs_roi']==load(OUT/'paired_full_vs_roi.json')
result={'status':'ALL39810_RAW_TICKS_MATRIX_INVERSES90_COUNTER_PATHS_AND_PAIR_TABLES_INDEPENDENTLY_VERIFIED',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(ROOT/'protocol/crop_v1.json'),
        'raw_source_condition_ticks':raw_ticks,'raw_boxes_matrix_inverse_verified':boxes,'maximum_inverse_absolute_error':inverse_error,
        'counter_observation_ticks':obs_ticks,'native_ROI_centers_recomputed':centers,'independent_counter_paths':paths,
        'publisher6_formal_event_conditions':formal,'multiple_optimal_event_assignment_conditions':ambiguous,
        'paired_full_vs_crop_conditions':len(flat),'independent_native_crop_checks':8,'actual_NN_input_array_checks':24,'actual_model_NN_anchor_hash_rows':120,'actual_input_array_bytes_exact_to_prior_fixed_crop':True,
        'new_network_forwards':0,'new_training_updates':0,'new_independent_test':False,'PYNQ5FPS_proven':False,'whole_goal_complete':False}
file=ROOT/'results/independent_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n')
file=ROOT/'results/paired_full_vs_roi.csv';assert not file.exists()
with file.open('x',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
print(json.dumps(result))
