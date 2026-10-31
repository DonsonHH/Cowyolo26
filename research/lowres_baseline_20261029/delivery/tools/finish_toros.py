"""Resume only the remaining Toros forward passes; all completed files immutable."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import os,socket,json,hashlib,gzip,time,resource
import numpy as np,cv2,torch,ultralytics
from ultralytics import YOLO
import run_baseline_v2 as prior
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/baseline'
def load(p):return json.loads(Path(p).read_text())
def loadgz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def sha(p):return prior.sha(p)
def save(p,v):return prior.save(p,v)
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01' and torch.cuda.is_available()
    assert ultralytics.__version__=='8.4.63';cv2.setNumThreads(1);torch.set_num_threads(4)
    protocol=load(ROOT/'protocol/baseline_v2_path_fix.json');old=load(ROOT/'protocol/baseline_v1.json')
    assert protocol['supersedes_v1_sha256']==sha(ROOT/'protocol/baseline_v1.json')
    assert protocol['conditions']==old['conditions'] and protocol['counter_kwargs']==old['counter_kwargs'] and protocol['prediction']==old['prediction']
    assert protocol['videos'][0]==old['videos'][0] and protocol['videos'][1]['sha256']==old['videos'][1]['sha256']
    assert not (OUT/'toros').exists() and not (OUT/'summary.json').exists()
    prior.protocol=protocol;video_metrics=[];completed=[];prior_records=0
    validation=load(OUT/'validation_metrics.json');assert len(validation)==12
    for condition in protocol['conditions']:
        file=OUT/(condition['condition']+'_validation_predictions.json.gz');rows=loadgz(file);assert len(rows)==1571;prior_records+=len(rows)
        completed.append({'file':file.relative_to(ROOT).as_posix(),'sha256':sha(file),'source_records':len(rows)})
        folder=OUT/'original'/condition['condition'];raw=folder/'raw_predictions.json.gz';rows=loadgz(raw);assert len(rows)==2175;prior_records+=len(rows)
        completed.append({'file':raw.relative_to(ROOT).as_posix(),'sha256':sha(raw),'source_records':len(rows)})
        current=load(folder/'stride5_summary.json');assert len(current)==2;video_metrics.extend(current)
    assert prior_records==44952
    save(OUT/'resume_gate.json',{'status':'REUSE_COMPLETED44952_SOURCE_RECORDS_AND_ONLY_RESUME_TOROS',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'completed_job':'130502FAILEDaftercompletedvalidationandoriginalbeforeTorosfileaccess',
        'completed_files':completed,'protocol_v1_sha256':sha(ROOT/'protocol/baseline_v1.json'),
        'protocol_v2_sha256':sha(ROOT/'protocol/baseline_v2_path_fix.json'),'new_network_forwards_expected':5748,
        'model_params_threshold_sampling_unchanged':True,'prior_source_records':prior_records})
    spec=protocol['videos'][1];assert sha(Path(spec['path']))==spec['sha256'];cap=cv2.VideoCapture(spec['path']);assert cap.isOpened()
    started=time.monotonic_ns();models={};forwards=0;hook_forwards=0;shapes=Counter()
    def start(predictor):
        if getattr(predictor,'_resume_hook',False):return
        previous=predictor.inference
        def inference(im,*args,**kwargs):
            nonlocal hook_forwards
            hook_forwards+=len(im);shapes[str(tuple(im.shape))]+=1;return previous(im,*args,**kwargs)
        predictor.inference=inference;predictor._resume_hook=True
    for c in protocol['models']:
        assert sha(Path(c['checkpoint']))==c['sha256'];model=YOLO(c['checkpoint']);model.add_callback('on_predict_start',start);models[c['name']]=model
    raw={c['condition']:[] for c in protocol['conditions']};batch=[];metadata=[]
    def flush():
        nonlocal forwards
        if not batch:return
        for condition in protocol['conditions']:
            model=models[condition['model']];cow=next(k for k,v in model.names.items() if v=='cow')
            outputs=model.predict(batch,imgsz=condition['input_size'],rect=False,batch=16,conf=.2,iou=.5,classes=[cow],max_det=300,half=False,augment=False,device=0,verbose=False)
            assert len(outputs)==len(batch);forwards+=len(batch)
            for out,meta in zip(outputs,metadata):
                boxes=out.boxes.xyxy.detach().cpu().numpy().astype(float).tolist();scores=out.boxes.conf.detach().cpu().numpy().astype(float).tolist()
                raw[condition['condition']].append({**meta,'predictions':[{'xyxy':box,'network_oriented_xyxy':box,'confidence':score,'class':cow} for box,score in zip(boxes,scores)]})
        batch.clear();metadata.clear()
    for frame in range(479):
        ok,image=cap.read();assert ok and image.shape==(1080,1920,3)
        batch.append(image);metadata.append({'frame0':frame,'time_s':frame/30})
        if len(batch)==16:flush()
    flush();cap.release();assert forwards==hook_forwards==5748
    tracker_updates=26100
    for condition in protocol['conditions']:
        cname=condition['condition'];folder=OUT/'toros'/cname;folder.mkdir(parents=True,exist_ok=False);prior.savegz(folder/'raw_predictions.json.gz',raw[cname])
        for stride in [6,1]:
            trace=prior.counter_replay(spec,raw[cname],models[condition['model']].names,stride);tracker_updates+=len(trace['observations']);current=[]
            for key in ['confirmed_only_events','handoff_events']:
                events=trace[key];record={'scene':'toros','condition':cname,'model':condition['model'],'input_size':condition['input_size'],
                    'sample_stride':stride,'nominal_inference_Hz':30/stride,'counter':key,'down':sum(e['direction']=='A->B' for e in events),
                    'up':sum(e['direction']=='B->A' for e in events),'events':events,'human_down_total':None,'absolute_down_total_error':None,
                    'formal_event_metrics':prior.evaluate_events(spec['reference_events'],events,2.)}
                current.append(record);video_metrics.append(record)
            prior.savegz(folder/('stride'+str(stride)+'_counter_trace.json.gz'),trace);save(folder/('stride'+str(stride)+'_summary.json'),current)
    assert tracker_updates==32808 and len(video_metrics)==72
    for f in completed:assert sha(ROOT/f['file'])==f['sha256']
    save(OUT/'video_metrics.json',video_metrics)
    summary={'status':'ALL12_LOWRES_FROZEN_BASELINES_VALIDATION_AND_TWO_SOURCE_COUNTER_REPLAYS_COMPLETE','created_UTC':datetime.now(timezone.utc).isoformat(),
    'Slurm_JOB_ID':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/baseline_v2_path_fix.json'),
    'original_protocol_sha256':sha(ROOT/'protocol/baseline_v1.json'),'model_conditions':12,'actual_detector_source_image_forwards':prior_records+forwards,
    'prior_completed_source_prediction_records':prior_records,'resumed_new_detector_source_image_forwards':forwards,
    'predictor_inference_image_hook_count_current_resume':hook_forwards,'prior_in_memory_predictor_hook_counter_not_recovered_after_failure':True,
    'predictor_tensor_shapes_current_resume':dict(shapes),'tracker_updates':tracker_updates,'counter_paths':72,
    'prior_counter_baseline_gate':load(OUT/'baseline_counter_regression.json'),'validation_metrics':validation,'video_metrics':video_metrics,
    'new_training_updates':0,'identity_encoder_forwards':0,'original_human12_version_changed':False,'new_independent_test':False,
    'board_5FPS_verified':False,'whole_goal_complete':False,'resume_wall_s':(time.monotonic_ns()-started)/1e9,
    'resume_peak_process_RSS_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    save(OUT/'summary.json',summary);save(ROOT/'results/artifact_manifest.json',[{'relative_file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(OUT.rglob('*')) if f.is_file()])
    print(json.dumps({k:v for k,v in summary.items() if k not in ['validation_metrics','video_metrics']}),flush=True)
if __name__=='__main__':main()
