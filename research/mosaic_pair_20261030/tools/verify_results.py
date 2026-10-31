"""Independent training-log reconciliation, geometry and event recomputation."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter,defaultdict
import json,gzip,hashlib,math,importlib.util,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OUT=ROOT/'delivery/results/evaluation_v2'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def gz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mod(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
geo=mod('mosaic_independent_geometry',PROJECT/'detector_torso_pairs_20261029/tools/independent_geometry.py')
scanner=mod('mosaic_independent_stable_runs',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py')
p=load(ROOT/'protocol/training_v1.json');ev=load(ROOT/'protocol/evaluation_v2.json');s=load(OUT/'summary.json')
assert s['actual_source_image_forwards']==s['actual_inference_hook_image_calls']==25350
assert s['protocol_sha256']==sha(ROOT/'protocol/evaluation_v2.json')
frozen=load(ROOT/'delivery/results/all_six_checkpoints_frozen.json');assert len(frozen['models'])==6
training=[];all_schedules={};all_turns={};batch_records=gradient_records=image_presentations=0
for c in p['conditions']:
    folder=ROOT/'delivery/results/training'/c['name'];r=load(folder/'condition_complete.json')
    assert r['condition']==c and r['initial_state_digest']==p['expected_initial_state_digests'][str(c['seed'])]
    assert sha(folder/'weights/last.pt')==r['last_checkpoint_sha256']
    f=next(x for x in frozen['models'] if x['condition']['name']==c['name']);assert f['sha256']==r['last_checkpoint_sha256']
    for name,key in [('actual_batches.jsonl','batch_audit_sha256'),('actual_gradient_updates.jsonl','gradient_audit_sha256'),('optimizer_step_batch_indices.json','optimizer_step_indices_sha256')]:assert sha(folder/name)==r[key]
    batches=[json.loads(line) for line in (folder/'actual_batches.jsonl').read_text(encoding='utf-8').splitlines()]
    grads=[json.loads(line) for line in (folder/'actual_gradient_updates.jsonl').read_text(encoding='utf-8').splitlines()]
    schedule=load(folder/'optimizer_step_batch_indices.json')
    assert len(batches)==2130 and len(grads)==len(schedule)==1225
    assert [x['training_batch'] for x in batches]==list(range(1,2131))
    assert [x['optimizer_update'] for x in grads]==list(range(1,1226)) and [x['training_batch'] for x in grads]==schedule
    counts=Counter();presentations=0
    for i,b in enumerate(batches):
        n=25 if i%213==212 else 32
        assert b['NN_input_shape']==[n,3,192,192] and len(b['anchor_names'])==len(b['rotation_turns'])==n
        assert set(b['rotation_turns'])<={0,1,2,3} and np.isfinite(np.asarray(b['loss'],dtype=float)).all()
        assert len(b['NN_input_sha256'])==len(b['bbox_tensor_sha256'])==64 and b['label_rows']>0
        counts.update(b['rotation_turns']);presentations+=n
    assert presentations==68090 and {str(k):v for k,v in counts.items()}==r['actual_rotation_counts']
    assert all(x['finite_tensors']>=x['nonzero_tensors']>0 for x in grads)
    assert r['actual_persisted_batch_rows']==2130 and r['actual_persisted_gradient_rows']==1225 and r['optimizer_updates']==1225
    all_schedules[c['name']]=schedule;all_turns[c['name']]=[b['rotation_turns'] for b in batches]
    batch_records+=len(batches);gradient_records+=len(grads);image_presentations+=presentations
    training.append({'condition':c['name'],'batches':2130,'updates':1225,'image_presentations':presentations,'finite_gradient_gate_rows':1225,
        'input_digest_rows':2130,'raw_full_gradient_arrays_saved':False})
for seed in [26,27,28]:
    a,b=('mosaic100_seed'+str(seed),'mosaic050_seed'+str(seed))
    assert all_schedules[a]==all_schedules[b] and all_turns[a]==all_turns[b]
def inverse(raw,shape,crop,rotate):
    h,w=shape;g=min(192/h,192/w);px,py=round((192-w*g)/2-.1),round((192-h*g)/2-.1);out=[]
    for r in raw:
        a,b,c,d=[float(v) for v in r[:4]]
        a,c=max(0,min(w,(a-px)/g)),max(0,min(w,(c-px)/g))
        b,d=max(0,min(h,(b-py)/g)),max(0,min(h,(d-py)/g))
        out.append([b+crop[0],crop[3]-c,d+crop[0],crop[3]-a] if rotate else [a+crop[0],b+crop[1],c+crop[0],d+crop[1]])
    return out
def temporal(reference,predictions):
    best=(-1,float('inf'));winners=[]
    def search(i,used,pairs,cost):
        nonlocal best,winners
        if i==len(reference):
            score=(len(pairs),cost)
            if score[0]>best[0] or score[0]==best[0] and cost<best[1]-1e-10:best=score;winners=[pairs]
            elif score[0]==best[0] and abs(cost-best[1])<1e-10:winners.append(pairs)
            return
        search(i+1,used,pairs,cost)
        for j,pred in enumerate(predictions):
            error=abs(pred['time_s']-reference[i]['time_s'])
            if j not in used and error<=2:search(i+1,used|{j},pairs+[(i,j)],cost+error)
    search(0,set(),[],0.)
    return best,winners
val=load(ROOT/'input/validation_images.json');byfile={r['file_name']:r for r in val}
problems=reference_checks=raw_video_rows=boxes_checked=observations=paths=formal_paths=0;max_inverse=0.;valsummary=[]
for c in p['conditions']:
    name=c['name'];folder=OUT/name
    with np.load(folder/'validation_all_raw.npz') as ar:raw=ar['raw']
    records=gz(folder/'validation_predictions.json.gz');assert len(records)==1571 and raw.shape==(1571,300,6)
    matched=predicted=0
    for row,head in zip(records,raw):
        source=byfile[row['file_name']];assert row['source_sha256']==source['sha256']
        refs=[geo.envelope(geo.intersection(geo.corners(r['bbox_xywh_angle_rad']),[0,0,1280,720])) for r in source['reference_annotations']]
        assert len(refs)==len(row['reference_AABB'])
        for a,b in zip(refs,row['reference_AABB']):assert max(abs(x-y) for x,y in zip(a,b))<1e-8;reference_checks+=1
        selected=head[head[:,4]>=.2];assert len(selected)==len(row['predictions'])
        native=inverse(selected,(1280,720),[0,0,1280,720],True)
        for a,b,q in zip(native,row['predictions'],selected):
            error=max(abs(x-y) for x,y in zip(a,b['xyxy']));assert error<.001;max_inverse=max(max_inverse,error)
            assert b['confidence']==float(q[4]) and b['class']==0;boxes_checked+=1
        matrix=[[geo.iou(a,b['xyxy']) for b in row['predictions']] for a in refs]
        optimum,_=geo.independent_best_matching(matrix,.5);given=row['matches']
        assert len(given)==optimum[0] and abs(sum(r['IoU'] for r in given)-optimum[1])<1e-8
        assert len({r['reference_index'] for r in given})==len({r['prediction_index'] for r in given})==len(given)
        for pair in given:assert pair['IoU']>=.5 and abs(pair['IoU']-matrix[pair['reference_index']][pair['prediction_index']])<1e-8
        matched+=len(given);predicted+=len(row['predictions']);problems+=1
    metric=next(r for r in s['validation_metrics'] if r['condition']==name)
    assert [metric[k] for k in ['TP','unmatched_reference','unmatched_prediction']]==[matched,1864-matched,predicted-matched]
    valsummary.append(metric)
    for video in ev['videos']:
        scene=folder/video['name'];rows=gz(scene/'raw_predictions.json.gz')
        with np.load(scene/'all_raw.npz') as ar:raw=ar['raw']
        assert raw.shape==(len(rows),300,6) and np.isfinite(raw).all() and np.all(raw[:,:,5]==0)
        assert [r['frame0'] for r in rows]==list(range(0,video['decode_end_exclusive'],video['inference_stride']))
        x0,y0,x1,y1=video['detection_crop_xyxy'];rot=video['orientation']=='clockwise90';shape=(x1-x0,y1-y0) if rot else (y1-y0,x1-x0)
        for row,head in zip(rows,raw):
            selected=head[head[:,4]>=.2];assert len(selected)==len(row['predictions'])
            for a,b,q in zip(inverse(selected,shape,video['detection_crop_xyxy'],rot),row['predictions'],selected):
                error=max(abs(x-y) for x,y in zip(a,b['xyxy']));assert error<.001;max_inverse=max(max_inverse,error)
                assert b['confidence']==float(q[4]) and b['class']==0;boxes_checked+=1
            raw_video_rows+=1
        for stride in video['counter_replay_strides']:
            trace=gz(scene/('stride'+str(stride)+'_counter_trace.json.gz'));obs=trace['observations']
            assert [r['frame0'] for r in obs]==list(range(0,video['decode_end_exclusive'],stride));observations+=len(obs)
            byframe=defaultdict(list)
            for r in trace['post_tracker']:byframe[r['frame0']].append(r)
            for row in obs:
                positions={};ids=set()
                for post in byframe[row['frame0']]:
                    tid=post['track_id']
                    if tid is None:continue
                    ids.add(tid);a,b,c,d=post['xyxy'];cx=(a+c)/(2*video['width']);cy=(b+d)/(2*video['height'])
                    if video['perpendicular_ROI'][0]<(cx if video['axis']=='y' else cy)<video['perpendicular_ROI'][1]:positions[str(tid)]=cy if video['axis']=='y' else cx
                assert positions==row['confirmed_positions'] and sorted(ids)==row['confirmed_IDs']
            for kind,admit in [('confirmed_only_events',False),('handoff_events',True)]:
                events,_=scanner.batch_events(obs,admit);assert events==trace[kind];paths+=1
                scoped=[r for r in events if video['scope_start_frame0']<=r['frame0']<video['scope_end_exclusive']]
                metric=next(r for r in s['video_metrics'] if r['condition']==name and r['scene']==video['name'] and r['stride']==stride and r['counter']==kind)
                assert metric['events']==scoped and metric['down']==sum(r['direction']=='A->B' for r in scoped) and metric['up']==sum(r['direction']=='B->A' for r in scoped)
                if video['name']=='toros':
                    optimum,winners=temporal(video['reference_events'],scoped);score=metric['formal_event_metrics']
                    pairs=sorted((r['reference_index'],r['prediction_index']) for r in score['pairs']);assert pairs in winners and score['temporally_matched']==optimum[0]
                    correct=sum(video['reference_events'][a]['direction']==scoped[b]['direction'] for a,b in pairs)
                    assert [score[k] for k in ['TP','FP','FN']]==[correct,len(scoped)-correct,6-correct];formal_paths+=1
                else:assert metric['formal_event_metrics'] is None
assert [problems,reference_checks,raw_video_rows,observations,paths,formal_paths]==[9426,11184,15924,16404,36,24]
anchors=load(OUT/'input_tensor_anchors.json');assert len(anchors)==48
for r in anchors:assert r['tensor_sha256']==ev['expected_NN_input_hashes'][r['scene']+'_f'+str(r['frame0'])+'_s192']
assert batch_records==12780 and gradient_records==7350 and image_presentations==408540
result={'status':'ALL6_TRAINING_LOGS9426_IMAGE_MATCHES_AND36_EVENT_PATHS_RECONCILED','created_UTC':datetime.now(timezone.utc).isoformat(),
    'training_batch_rows_checked':batch_records,'gradient_gate_record_rows_checked':gradient_records,'actual_training_image_presentations':image_presentations,
    'paired_rotation_schedules_and_optimizer_indices_exact':3,'raw_full_gradient_arrays_saved':False,
    'validation_matching_problems':problems,'validation_reference_boxes':reference_checks,'raw_video_rows':raw_video_rows,'boxes_inverse_checked':boxes_checked,
    'maximum_inverse_error_pixels':max_inverse,'counter_observation_ticks':observations,'counter_paths':paths,'publisher_temporal_assignment_paths':formal_paths,
    'actual_NN_input_anchor_hashes_checked':48,'validation_metrics':valsummary,'new_model_forwards_in_this_verifier':0,'whole_goal_complete':False}
target=ROOT/'results/independent_verification.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='validation_metrics'}))
