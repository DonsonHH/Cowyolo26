"""Evaluate all15 fixed final weights after one common freeze; full input only."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import os,sys,socket,json,gzip,hashlib,time,importlib.util
import numpy as np,cv2,torch,ultralytics
from ultralytics import YOLO
from common import ROOT,sha,save_new
from geometry import reference,assign
def load(p):return json.loads(Path(p).read_text())
def loadgz(p):return json.loads(gzip.decompress(p.read_bytes()))
def savegz(p,value):
    assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True)
    with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write(json.dumps(value,separators=(',',':')).encode())
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01' and torch.cuda.is_available()
    assert ultralytics.__version__=='8.4.63';torch.set_num_threads(4);cv2.setNumThreads(1)
    p=load(ROOT/'protocol/evaluation_v1.json');freeze=load(ROOT/'results/all_checkpoints_frozen.json')
    assert freeze['status']=='ALL15_LAST_EPOCH_WEIGHTS_AND3_HISTORICAL_CONTROLS_FROZEN_BEFORE_NEW_VIDEO_INFERENCE'
    assert freeze['source_video_Toros_or_final_candidate_inference_before_freeze'] is False and len(freeze['conditions'])==15
    for row in freeze['conditions']:assert sha(row['last_checkpoint'])==row['last_checkpoint_sha256']
    for row in freeze['historical_controls']:assert sha(row['checkpoint'])==row['checkpoint_sha256']
    for name,digest in p['input_file_sha256'].items():assert sha(ROOT/'input'/name)==digest
    baseline=Path(p['baseline_root_remote']);assert sha(baseline/'tools/run_baseline_v2.py')==p['old_counter_module_sha256']
    spec=importlib.util.spec_from_file_location('fixed_prior_counter_replay',baseline/'tools/run_baseline_v2.py');prior=importlib.util.module_from_spec(spec)
    sys.path[:0]=[str(baseline/'input'),str(baseline/'tools')];sys.modules[spec.name]=prior;spec.loader.exec_module(prior)
    prior.protocol=load(baseline/'protocol/baseline_v2_path_fix.json')
    assert prior.protocol['counter_kwargs']==p['counter_kwargs'] and prior.protocol['prediction']==p['prediction']
    out=ROOT/'results/evaluation';out.mkdir(exist_ok=False);started=time.monotonic_ns()
    gate=[];cachedticks=0
    for condition in p['cached_control_conditions']:
        for video in p['videos']:
            folder=baseline/'results/baseline'/video['name']/condition['condition'];raw=loadgz(folder/'raw_predictions.json.gz')
            for stride in video['counter_replay_strides']:
                current=prior.counter_replay(video,raw,{19:'cow'} if condition['model']=='official' else {0:'cow'},stride)
                assert json.loads(json.dumps(current))==loadgz(folder/('stride'+str(stride)+'_counter_trace.json.gz'))
                cachedticks+=len(current['observations']);gate.append({'condition':condition['condition'],'scene':video['name'],'stride':stride,'entire_trace_exact':True})
    assert cachedticks==16404 and len(gate)==18
    save_new(out/'cached_control_regression_gate.json',{'traces':gate,'tracker_updates':cachedticks,'counter_paths':36,'new_model_forwards_at_gate':0})
    forwards=hookcount=0;shapes=Counter();models={};conditions=p['new_conditions'];valmetrics=[];videometrics=[];allmetrics=[]
    def onstart(predictor):
        if getattr(predictor,'_factor_hooked',False):return
        original=predictor.inference
        def wrapped(images,*a,**kw):
            nonlocal hookcount
            hookcount+=len(images);shapes[str(tuple(images.shape))]+=1;return original(images,*a,**kw)
        predictor.inference=wrapped;predictor._factor_hooked=True
    for condition in conditions:
        row=next(r for r in freeze['conditions'] if r['condition']['condition_id']==condition['condition'])
        model=YOLO(row['last_checkpoint']);assert model.names=={0:'cow'};model.add_callback('on_predict_start',onstart);models[condition['condition']]=model
    def network(c,images,metadata,height,rotate):
        nonlocal forwards
        result=models[c['condition']].predict(images,imgsz=c['input_size'],rect=False,batch=16,conf=.2,iou=.5,classes=[0],max_det=300,half=False,augment=False,device=0,verbose=False)
        assert len(result)==len(images);forwards+=len(images);rows=[]
        for prediction,meta in zip(result,metadata):
            boxes=prediction.boxes.xyxy.detach().cpu().numpy().astype(float).tolist();scores=prediction.boxes.conf.detach().cpu().numpy().astype(float).tolist()
            predictions=[]
            for box,score in zip(boxes,scores):
                x1,y1,x2,y2=box;restored=[y1,height-x2,y2,height-x1] if rotate else box
                predictions.append({'network_oriented_xyxy':box,'xyxy':restored,'confidence':score,'class':0})
            rows.append({**meta,'predictions':predictions})
        return rows
    images=load(ROOT/'input/validation_images.json');assert len(images)==1571
    refs={row['file_name']:[reference(r)['visible_reference_AABB'] for r in row['reference_annotations']] for row in images}
    rawval={c['condition']:[] for c in conditions}
    for start in range(0,len(images),16):
        batch=images[start:start+16];pixels=[];metadata=[]
        for row in batch:
            assert sha(row['image_alias'])==row['sha256'];image=cv2.imread(row['image_alias']);assert image.shape==(720,1280,3)
            pixels.append(np.rot90(image,k=-1).copy());metadata.append({'file_name':row['file_name'],'source_sha256':row['sha256'],'capture_date':row['capture_date']})
        for c in conditions:
            rows=network(c,pixels,metadata,720,True)
            for row in rows:
                matches,_=assign(refs[row['file_name']],[r['xyxy'] for r in row['predictions']]);row['reference_AABB']=refs[row['file_name']]
                row['matches']=[{'reference_index':i,'prediction_index':j,'IoU':iou} for i,j,iou in matches]
            rawval[c['condition']].extend(rows)
        if start%320==0:print(json.dumps({'stage':'validation','done_images':start+len(batch),'image_forwards':forwards}),flush=True)
    for c in conditions:
        rows=rawval[c['condition']];tp=sum(len(r['matches']) for r in rows);count=sum(len(r['predictions']) for r in rows);gt=sum(len(r['reference_AABB']) for r in rows);assert gt==1864
        m={**c,'images':1571,'references':1864,'matched':tp,'unmatched_reference':gt-tp,'unmatched_prediction':count-tp,
           'recall':tp/gt,'precision_vs_reference':tp/count if count else None};valmetrics.append(m)
        savegz(out/(c['condition']+'_validation_predictions.json.gz'),rows)
    del rawval;save_new(out/'validation_metrics.json',valmetrics);ticks=0
    for video in p['videos']:
        assert sha(video['path'])==video['sha256'];cap=cv2.VideoCapture(video['path']);assert cap.isOpened()
        raw={c['condition']:[] for c in conditions};pixels=[];metadata=[]
        def flush():
            if not pixels:return
            for c in conditions:raw[c['condition']].extend(network(c,pixels,metadata,video['height'],video['orientation']=='clockwise90'))
            pixels.clear();metadata.clear()
        for frame in range(video['decode_end_exclusive']):
            ok,native=cap.read();assert ok and native.shape==(video['height'],video['width'],3)
            if frame%video['inference_stride']:continue
            pixels.append(np.rot90(native,k=-1).copy() if video['orientation']=='clockwise90' else native)
            metadata.append({'frame0':frame,'time_s':frame/video['fps']})
            if len(pixels)==16:flush()
            if frame%2500==0:print(json.dumps({'stage':video['name'],'frame0':frame,'image_forwards':forwards}),flush=True)
        flush();cap.release()
        for c in conditions:
            folder=out/video['name']/c['condition'];folder.mkdir(parents=True,exist_ok=False);savegz(folder/'raw_predictions.json.gz',raw[c['condition']])
            for stride in video['counter_replay_strides']:
                trace=prior.counter_replay(video,raw[c['condition']],{0:'cow'},stride);ticks+=len(trace['observations']);metrics=[]
                for kind in ['confirmed_only_events','handoff_events']:
                    events=[r for r in trace[kind] if video['scope_start_frame0']<=r['frame0']<video['scope_end_exclusive']]
                    row={**c,'scene':video['name'],'sample_stride':stride,'nominal_inference_Hz':video['fps']/stride,'counter':kind,
                      'events':events,'down':sum(e['direction']=='A->B' for e in events),'up':sum(e['direction']=='B->A' for e in events),
                      'human_down_total':12 if video['name']=='original' else None,'absolute_down_total_error':None,'formal_event_metrics':None}
                    if video['name']=='original':row['absolute_down_total_error']=abs(row['down']-12)
                    else:row['formal_event_metrics']=prior.evaluate_events(video['reference_events'],events,2.)
                    metrics.append(row);videometrics.append(row)
                savegz(folder/('stride'+str(stride)+'_counter_trace.json.gz'),trace);save_new(folder/('stride'+str(stride)+'_summary.json'),metrics)
        print(json.dumps({'scene_complete':video['name'],'image_forwards':forwards,'tracker_ticks':ticks}),flush=True)
    assert forwards==hookcount==63375 and ticks==41010 and len(videometrics)==90 and len(valmetrics)==15
    save_new(out/'video_metrics.json',videometrics)
    result={'status':'ALL15_NEW_LOWRES_FACTOR_SEEDS63375_FORWARDS90_COUNTER_PATHS_COMPLETE','created_UTC':datetime.now(timezone.utc).isoformat(),
      'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/evaluation_v1.json'),'all_weights_freeze_sha256':sha(ROOT/'results/all_checkpoints_frozen.json'),
      'actual_detector_source_image_forwards':forwards,'predictor_hook_image_forwards':hookcount,'predictor_tensor_shapes':dict(shapes),
      'validation_image_conditions':23565,'new_tracker_updates':ticks,'new_counter_paths':90,'cached_control_regression_paths':36,
      'validation_metrics':valmetrics,'video_metrics':videometrics,'new_training_updates':0,'whole_goal_complete':False,
      'no_source_or_Toros_choice_of_weights':True,'new_independent_test':False,'PYNQ5FPS_proven_by_offline_study':False,
      'elapsed_s':(time.monotonic_ns()-started)/1e9}
    save_new(out/'summary.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['validation_metrics','video_metrics']}),flush=True)
if __name__=='__main__':main()
