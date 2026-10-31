"""Independent geometry, matching, stable-run events and raw-cache regression."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json,gzip,hashlib,importlib.util,sys,math
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
OUT=ROOT/'delivery/results/study_v2'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def gz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
geo=module('independent_photometric_geometry',PROJECT/'detector_torso_pairs_20261029/tools/independent_geometry.py')
scanner=module('independent_photometric_runs',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py')

def temporal_optimum(reference,predictions):
    best=(-1,float('inf'));winners=[]
    def search(i,used,pairs,cost):
        nonlocal best,winners
        if i==len(reference):
            candidate=(len(pairs),cost)
            if candidate[0]>best[0] or candidate[0]==best[0] and cost<best[1]-1e-10:best=candidate;winners=[pairs]
            elif candidate[0]==best[0] and abs(cost-best[1])<1e-10:winners.append(pairs)
            return
        search(i+1,used,pairs,cost)
        for j,row in enumerate(predictions):
            error=abs(row['time_s']-reference[i]['time_s'])
            if j not in used and error<=2:search(i+1,used|{j},pairs+[(i,j)],cost+error)
    search(0,set(),[],0.)
    return best,winners

def inverse(raw,shape,crop,rotated):
    h,w=shape;g=min(192/h,192/w)
    px,py=round((192-w*g)/2-.1),round((192-h*g)/2-.1)
    boxes=[]
    for r in raw:
        a=max(0,min(w,(float(r[0])-px)/g));b=max(0,min(h,(float(r[1])-py)/g))
        c=max(0,min(w,(float(r[2])-px)/g));d=max(0,min(h,(float(r[3])-py)/g))
        matrix=np.array([[0,1,crop[0]],[-1,0,crop[3]],[0,0,1]],float) if rotated else np.array([[1,0,crop[0]],[0,1,crop[1]],[0,0,1]],float)
        corners=np.array([[a,b,1],[c,b,1],[c,d,1],[a,d,1]])@matrix.T
        boxes.append([*corners[:,:2].min(0),*corners[:,:2].max(0)])
    return boxes

p=load(ROOT/'protocol/study_v2.json');s=load(OUT/'summary.json')
assert s['protocol_sha256']==sha(ROOT/'protocol/study_v2.json')
assert s['actual_total_forwards']==25350 and s['actual_ORT_forwards']=={c:{'FP32':4225,'QDQ':4225} for c in p['conditions']}
gate=load(OUT/'baseline_gate.json')
assert gate['baseline_raw_arrays_byte_exact']==8450 and gate['baseline_video_input_tensors_byte_exact']==2654
assert gate['baseline_full_tracker_traces_exact']==6 and gate['new_transform_forwards_at_gate']==0
manifest=load(ROOT/'delivery/results/artifact_manifest.json')
for row in manifest:
    f=ROOT/'delivery'/row['file'];assert f.stat().st_size==row['bytes'] and sha(f)==row['sha256']
images=load(ROOT/'input/validation_images.json')
refs_by_image=[];max_geom=0.;problems=reference_boxes=pred_boxes=0;max_inverse=0.
for row in images:
    refs_by_image.append([geo.envelope(geo.intersection(geo.corners(a['bbox_xywh_angle_rad']),[0,0,1280,720])) for a in row['reference_annotations']])
old=PROJECT/'pynq_rot192_eval_20261029/delivery/results/quality_v2'
oldraw={}
with np.load(old/'validation_all_raw.npz') as archive:oldraw={m:archive[m] for m in ['FP32','QDQ']}
baseline_raw_exact=0;video_ticks=video_boxes=observations=event_paths=formal_paths=0
validation_rows=[];video_rows=[]
for condition in p['conditions']:
    with np.load(OUT/condition/'validation_all_raw.npz') as archive:
        for mode in ['FP32','QDQ']:
            raw=archive[mode]
            records=gz(OUT/condition/(mode+'_validation_predictions.json.gz'))
            assert raw.shape==(1571,300,6) and len(records)==1571 and np.isfinite(raw).all()
            if condition=='none':assert raw.tobytes()==oldraw[mode].tobytes();baseline_raw_exact+=len(raw)
            tp=total=0
            for i,(r,a) in enumerate(zip(records,raw)):
                assert r['file_name']==images[i]['file_name'] and r['source_sha256']==images[i]['sha256']
                refs=refs_by_image[i]
                assert len(refs)==len(r['reference_AABB'])
                for u,v in zip(refs,r['reference_AABB']):
                    delta=max(abs(x-y) for x,y in zip(u,v));assert delta<1e-8;max_geom=max(max_geom,delta);reference_boxes+=1
                chosen=a[a[:,4]>=.2];pred=r['predictions'];assert len(pred)==len(chosen)
                expect=inverse(chosen,(1280,720),[0,0,1280,720],True)
                for u,v,head in zip(expect,pred,chosen):
                    delta=max(abs(x-y) for x,y in zip(u,v['xyxy']));assert delta<.0003;max_inverse=max(max_inverse,delta)
                    assert v['confidence']==float(head[4]) and v['class']==0
                matrix=[[geo.iou(a,b['xyxy']) for b in pred] for a in refs]
                optimum,_=geo.independent_best_matching(matrix,.5);matched=r['matches']
                assert len(matched)==optimum[0] and abs(sum(x['IoU'] for x in matched)-optimum[1])<1e-8
                assert len({x['reference_index'] for x in matched})==len({x['prediction_index'] for x in matched})==len(matched)
                for pair in matched:assert abs(pair['IoU']-matrix[pair['reference_index']][pair['prediction_index']])<1e-8
                tp+=len(matched);total+=len(pred);problems+=1;pred_boxes+=len(pred)
            metric=next(r for r in s['validation_metrics'] if r['condition']==condition and r['mode']==mode)
            assert [metric[k] for k in ['TP','unmatched_reference','unmatched_prediction']]==[tp,1864-tp,total-tp]
            assert metric['recall']==tp/1864 and metric['precision_vs_reference']==tp/total
            validation_rows.append(metric)
    for video in p['videos']:
        x0,y0,x1,y1=video['detection_crop_xyxy'];rotated=video['orientation']=='clockwise90'
        shape=(x1-x0,y1-y0) if rotated else (y1-y0,x1-x0)
        prior={}
        if condition=='none':
            with np.load(old/(video['name']+'_all_raw.npz')) as archive:prior={m:archive[m] for m in ['FP32','QDQ']}
        with np.load(OUT/condition/(video['name']+'_all_raw.npz')) as archive:
            for mode in ['FP32','QDQ']:
                array=archive[mode]
                folder=OUT/condition/video['name']/mode
                raw=gz(folder/'raw_predictions.json.gz')
                assert [r['frame0'] for r in raw]==list(range(0,video['decode_end_exclusive'],video['inference_stride']))
                assert array.shape==(len(raw),300,6) and np.isfinite(array).all() and np.all(array[:,:,5]==0)
                if condition=='none':
                    assert array.tobytes()==prior[mode].tobytes() and raw==gz(old/video['name']/mode/'raw_predictions.json.gz')
                    baseline_raw_exact+=len(raw)
                for r,a in zip(raw,array):
                    assert r['time_s']==r['frame0']/video['fps']
                    chosen=a[a[:,4]>=.2];pred=r['predictions'];assert len(chosen)==len(pred)
                    expected=inverse(chosen,shape,video['detection_crop_xyxy'],rotated)
                    for u,v,head in zip(expected,pred,chosen):
                        delta=max(abs(x-y) for x,y in zip(u,v['xyxy']));assert delta<.0003;max_inverse=max(max_inverse,delta)
                        assert v['confidence']==float(head[4]) and v['class']==0;video_boxes+=1
                    video_ticks+=1
                for stride in video['counter_replay_strides']:
                    trace=gz(folder/('stride'+str(stride)+'_counter_trace.json.gz'));obs=trace['observations']
                    if condition=='none':assert trace==gz(old/video['name']/mode/('stride'+str(stride)+'_counter_trace.json.gz'))
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
                        assert row['confirmed_positions']==positions and row['confirmed_IDs']==sorted(ids)
                    for counter,admit in [('confirmed_only_events',False),('handoff_events',True)]:
                        events,_=scanner.batch_events(obs,admit);assert events==trace[counter];event_paths+=1
                        scoped=[r for r in events if video['scope_start_frame0']<=r['frame0']<video['scope_end_exclusive']]
                        row=next(r for r in s['video_metrics'] if all(r[k]==v for k,v in {'condition':condition,'scene':video['name'],'mode':mode,'stride':stride,'counter':counter}.items()))
                        assert row['events']==scoped and row['down']==sum(e['direction']=='A->B' for e in scoped) and row['up']==sum(e['direction']=='B->A' for e in scoped)
                        if video['name']=='toros':
                            optimum,winners=temporal_optimum(video['reference_events'],scoped)
                            score=row['formal_event_metrics'];pairs=sorted((e['reference_index'],e['prediction_index']) for e in score['pairs'])
                            assert pairs in winners and score['temporally_matched']==optimum[0]
                            correct=sum(video['reference_events'][a]['direction']==scoped[b]['direction'] for a,b in pairs)
                            assert [score[k] for k in ['TP','FP','FN']]==[correct,len(scoped)-correct,6-correct];formal_paths+=1
                        else:assert row['formal_event_metrics'] is None
                        video_rows.append({k:row[k] for k in ['condition','scene','mode','stride','counter','down','up','formal_event_metrics']})
assert [problems,reference_boxes,video_ticks,observations,event_paths,formal_paths,baseline_raw_exact]==[9426,11184,15924,16404,36,24,8450]
failed_preserved_arrays=0
for name in ['validation_all_raw.npz','original_all_raw.npz']:
    with np.load(ROOT/'delivery/results/study/none'/name) as failed,np.load(OUT/'none'/name) as successful:
        for mode in ['FP32','QDQ']:
            before,after=failed[mode],successful[mode]
            assert before.tobytes()==after.tobytes();failed_preserved_arrays+=len(before)
assert failed_preserved_arrays==7492
inputs=load(OUT/'input_hashes.json');assert len(inputs)==12675
old_inputs={(r['scene'],r['frame0']):r['input_tensor_sha256'] for r in load(old/'board_input_manifest.json')}
none=[r for r in inputs if r['condition']=='none' and r['role']!='validation'];assert len(none)==2654
assert all(r['tensor_sha256']==old_inputs[r['role'],r['frame0']] for r in none)
anchors=load(OUT/'pixel_controls.json');assert len(anchors)==30
for a in anchors:
    assert sha(OUT/a['pixel_file'])==a['pixel_sha256'] and sha(OUT/a['array_file'])==a['array_sha256']
    pixels=np.array(Image.open(OUT/a['pixel_file']).convert('RGB'))
    with np.load(OUT/a['array_file']) as ar:
        x=np.ascontiguousarray(pixels.transpose(2,0,1)[None],dtype=np.float32)*np.float32(1/255)
        assert x.tobytes()==ar['input'].tobytes() and hashlib.sha256(x.tobytes()).hexdigest()==a['tensor_sha256']
        top,left=a['geometry']['top'],a['geometry']['left'];width,height=a['geometry']['new_width'],a['geometry']['new_height']
        mask=np.ones((192,192),bool);mask[top:top+height,left:left+width]=False
        assert np.all(pixels[mask]==114)
verification={'status':'9426_GEOMETRY_MATCHES15924_RAW_VIDEO_ROWS36_EVENT_PATHS_AND8450_BASELINE_ARRAYS_RECOMPUTED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'validation_matching_problems':problems,'validation_reference_boxes':reference_boxes,
    'validation_predicted_boxes':pred_boxes,'maximum_independent_reference_geometry_error':max_geom,'maximum_inverse_coordinate_error':max_inverse,
    'video_raw_rows':video_ticks,'video_raw_boxes_inverse_checked':video_boxes,'counter_observation_ticks':observations,'counter_paths':event_paths,
    'publisher_temporal_assignment_paths':formal_paths,'baseline_raw_arrays_byte_exact':baseline_raw_exact,'baseline_video_input_hashes_exact':2654,
    'saved_actual_input_pixels_and_tensors_exact':30,'failed_v1_preserved_arrays_byte_exact_to_v2':failed_preserved_arrays,
    'validation_metrics':validation_rows,'video_metrics':video_rows,
    'new_model_forwards_in_this_verifier':0,'new_independent_test':False,'new_board_actions':0,'whole_goal_complete':False}
save(ROOT/'results/independent_verification.json',verification)
print(json.dumps({k:v for k,v in verification.items() if k not in ['validation_metrics','video_metrics']}))
