"""All four frozen detectors at192/256/320, square input; native5Hz counters."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict,Counter
import os,sys,socket,json,hashlib,gzip,csv,time,resource
import cv2,numpy as np,torch,ultralytics
from ultralytics import YOLO
from ultralytics.engine.results import Results
from ultralytics.trackers.byte_tracker import BYTETracker
from ultralytics.utils import YAML,IterableSimpleNamespace
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;sys.path.insert(0,str(ROOT/'input'))
from zone_counter import ZoneCounter
from confirmation_counter import ConfirmationHandoffCounter
from event_metrics import evaluate_events
from geometry import reference,assign
def load(p):return json.loads(Path(p).read_text())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(p,v):assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def savegz(p,v):
    assert not p.exists(),p
    with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write(json.dumps(v,separators=(',',':')).encode())
def counter_replay(spec,records,names,stride):
    cfg=YAML.load(ultralytics.__path__[0]+'/cfg/trackers/bytetrack.yaml');tracker=BYTETracker(IterableSimpleNamespace(**cfg))
    base=ZoneCounter(**protocol['counter_kwargs']);handoff=ConfirmationHandoffCounter(**protocol['counter_kwargs'])
    W,H=spec['width'],spec['height'];image=np.zeros((H,W,3),np.uint8);byframe={r['frame0']:r['predictions'] for r in records}
    observations=[];events=[];baseevents=[];post=[]
    for frame in range(0,spec['decode_end_exclusive'],stride):
        assert frame in byframe
        raw=np.asarray([[*r['xyxy'],r['confidence'],r['class']] for r in byframe[frame]],np.float32).reshape(-1,6)
        result=Results(orig_img=image,path='native_lowres_cache',names=names,boxes=torch.from_numpy(raw))
        out=tracker.update(result.boxes.cpu().numpy(),result.orig_img,feats=None)
        if len(out):result=result[out[:,-1].astype(int)];result.update(boxes=torch.as_tensor(out[:,:-1]))
        b=result.boxes;ids=b.id.int().cpu().tolist() if b.id is not None else [None]*len(b)
        active={tid for tid in ids if tid is not None};positions={};tentative={};time_s=frame/spec['fps']
        low,high=spec['perpendicular_ROI']
        for box,confidence,tid in zip(b.xyxy.cpu().tolist(),b.conf.cpu().tolist(),ids):
            x1,y1,x2,y2=box;cx=(x1+x2)/(2*W);cy=(y1+y2)/(2*H)
            post.append({'frame0':frame,'time_s':time_s,'track_id':tid,'confidence':confidence,'xyxy':box})
            cross=cx if spec['axis']=='y' else cy;axis=cy if spec['axis']=='y' else cx
            if tid is not None and low<cross<high:positions[tid]=axis
        for t in tracker.tracked_stracks:
            if t.is_activated:continue
            x1,y1,x2,y2=np.asarray(t.xyxy,np.float32).astype(float);cx=(x1+x2)/(2*W);cy=(y1+y2)/(2*H)
            if low<(cx if spec['axis']=='y' else cy)<high:tentative[int(t.track_id)]=cy if spec['axis']=='y' else cx
        for produced,target in [(base.update(time_s,positions),baseevents),(handoff.update(time_s,positions,tentative,active),events)]:
            for event in produced:event['frame0']=frame;target.append(event)
        observations.append({'frame0':frame,'time_s':time_s,'confirmed_positions':positions,'confirmed_IDs':sorted(active),
            'tentative_positions':tentative,'accepted_history':handoff.last_acceptances})
    return {'observations':observations,'post_tracker':post,'confirmed_only_events':baseevents,'handoff_events':events,'effective_tracker_config':cfg}
def regressions(models):
    reports=[]
    for source in load(ROOT/'input/regression_sources.json'):
        spec={'width':source['width'],'height':source['height'],'fps':source['fps'],'axis':source['axis'],
        'perpendicular_ROI':source['perpendicular_ROI'],'decode_end_exclusive':source['history_end_frame0_exclusive']}
        modelname='seed26' if source['name']=='original_seed26' else 'official';cow=next(k for k,v in models[modelname].names.items() if v=='cow')
        grouped=defaultdict(list)
        with Path(source['raw_path']).open(newline='') as f:
            for r in csv.DictReader(f):grouped[int(r[source['raw_frame_key']])].append({'xyxy':[float(r[k]) for k in ['x1','y1','x2','y2']],'confidence':float(r['confidence']),'class':cow})
        records=[{'frame0':f,'predictions':grouped[f]} for f in range(0,spec['decode_end_exclusive'],source['stride'])]
        result=counter_replay(spec,records,models[modelname].names,source['stride']);folder=Path(protocol['baseline_regression_root_remote'])/(source['name']+'__original_fused')
        def canonical(o):return json.loads(json.dumps(o))
        for current,file in [('observations','observations.json'),('handoff_events','handoff_events_all_history.json'),('confirmed_only_events','confirmed_only_events_all_history.json')]:
            assert canonical(result[current])==load(folder/file),(source['name'],current)
        report={'source':source['name'],'observation_ticks':len(result['observations']),'all_observations_and_both_event_lists_exact':True}
        if source['name']=='original_seed26':
            selected=[r for r in result['handoff_events'] if 8912<=r['frame0']<10874];assert sum(r['direction']=='A->B' for r in selected)==12
            report['confirmed12_total_retained']=True
        else:
            score=evaluate_events(source['reference_events'],result['handoff_events'],2.);assert score['TP']==6 and score['FP']==score['FN']==0;report['published6_score_exact']=True
        reports.append(report)
    return reports
protocol=load(ROOT/'protocol/baseline_v1.json')
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01' and torch.cuda.is_available()
    assert ultralytics.__version__=='8.4.63';cv2.setNumThreads(1);torch.set_num_threads(4)
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    for name,digest in protocol['input_sha256'].items():assert sha(ROOT/'input'/name)==digest
    assert sha(ROOT/'tools/geometry.py')==protocol['geometry_module_sha256']
    out=ROOT/'results/baseline';out.mkdir(exist_ok=False);started=time.monotonic_ns();models={};shape_counts=Counter();image_forwards=0;actual_hook_count=0
    def hook_start(predictor):
        if getattr(predictor,'_lowres_hooked',False):return
        function=predictor.inference
        def inference(im,*args,**kwargs):
            nonlocal actual_hook_count
            actual_hook_count+=len(im);shape_counts[str(tuple(im.shape))]+=1
            return function(im,*args,**kwargs)
        predictor.inference=inference;predictor._lowres_hooked=True
    for m in protocol['models']:
        assert sha(Path(m['checkpoint']))==m['sha256'];model=YOLO(m['checkpoint']);model.add_callback('on_predict_start',hook_start);models[m['name']]=model
    gate=regressions(models);save(out/'baseline_counter_regression.json',gate)
    input_images=load(ROOT/'input/validation_images.json');assert len(input_images)==1571
    geometry={r['file_name']:[reference(a)['visible_reference_AABB'] for a in r['reference_annotations']] for r in input_images}
    validation_predictions={c['condition']:[] for c in protocol['conditions']}
    def network(condition,images,metadata,native_height,rotate):
        nonlocal image_forwards
        model=models[condition['model']];cow=next(k for k,v in model.names.items() if v=='cow')
        outputs=model.predict(images,imgsz=condition['input_size'],rect=False,batch=16,conf=.2,iou=.5,classes=[cow],max_det=300,half=False,augment=False,device=0,verbose=False)
        assert len(outputs)==len(images);image_forwards+=len(images);records=[]
        for result,source in zip(outputs,metadata):
            boxes=result.boxes.xyxy.detach().cpu().numpy().astype(float).tolist();scores=result.boxes.conf.detach().cpu().numpy().astype(float).tolist()
            predictions=[]
            for box,score in zip(boxes,scores):
                x1,y1,x2,y2=box;back=[y1,native_height-x2,y2,native_height-x1] if rotate else box
                predictions.append({'xyxy':back,'network_oriented_xyxy':box,'confidence':score,'class':cow})
            records.append({**source,'predictions':predictions})
        return records
    for start in range(0,len(input_images),16):
        batch=input_images[start:start+16];images=[];metadata=[]
        for row in batch:
            path=Path(row['image_alias']);assert sha(path)==row['sha256'];im=cv2.imread(str(path));assert im.shape==(720,1280,3)
            images.append(np.rot90(im,k=-1).copy());metadata.append({'file_name':row['file_name'],'capture_date':row['capture_date'],'source_sha256':row['sha256']})
        for condition in protocol['conditions']:
            predictions=network(condition,images,metadata,720,True)
            for r in predictions:
                matches,_=assign(geometry[r['file_name']],[v['xyxy'] for v in r['predictions']])
                r['reference_AABB']=geometry[r['file_name']];r['matches']=[{'reference_index':a,'prediction_index':b,'IoU':v} for a,b,v in matches]
            validation_predictions[condition['condition']].extend(predictions)
        if start%320==0:print(json.dumps({'stage':'validation','source_images_done':start+len(batch),'image_forwards':image_forwards}),flush=True)
    validation_metrics=[]
    for condition in protocol['conditions']:
        records=validation_predictions[condition['condition']];tp=sum(len(r['matches']) for r in records);n=sum(len(r['predictions']) for r in records);gt=sum(len(r['reference_AABB']) for r in records)
        assert len(records)==1571 and gt==1864
        result={'condition':condition['condition'],'model':condition['model'],'input_size':condition['input_size'],'images':1571,'references':1864,
            'matched':tp,'unmatched_reference':gt-tp,'unmatched_prediction':n-tp,'recall':tp/gt,'precision_vs_reference':tp/n if n else None}
        savegz(out/(condition['condition']+'_validation_predictions.json.gz'),records);validation_metrics.append(result)
    save(out/'validation_metrics.json',validation_metrics);del validation_predictions
    video_metrics=[];all_ticks=0
    for spec in protocol['videos']:
        assert sha(Path(spec['path']))==spec['sha256'];cap=cv2.VideoCapture(spec['path']);assert cap.isOpened()
        raw={c['condition']:[] for c in protocol['conditions']};batch=[];meta=[];decoded=0
        def flush():
            if not batch:return
            for c in protocol['conditions']:
                raw[c['condition']].extend(network(c,batch,meta,spec['height'],spec['orientation']=='clockwise90'))
            batch.clear();meta.clear()
        for frame in range(spec['decode_end_exclusive']):
            ok,im=cap.read();assert ok,(spec['name'],frame);decoded+=1;assert im.shape==(spec['height'],spec['width'],3)
            if frame%spec['inference_stride']:continue
            batch.append(np.rot90(im,k=-1).copy() if spec['orientation']=='clockwise90' else im)
            meta.append({'frame0':frame,'time_s':frame/spec['fps']})
            if len(batch)==16:flush()
            if frame%1250==0:print(json.dumps({'stage':spec['name'],'source_frame0':frame,'image_forwards':image_forwards}),flush=True)
        flush();cap.release();assert decoded==spec['decode_end_exclusive']
        for condition in protocol['conditions']:
            cname=condition['condition'];records=raw[cname];folder=out/spec['name']/cname;folder.mkdir(parents=True)
            expected=len(range(0,spec['decode_end_exclusive'],spec['inference_stride']));assert len(records)==expected
            savegz(folder/'raw_predictions.json.gz',records)
            for stride in spec['counter_replay_strides']:
                result=counter_replay(spec,records,models[condition['model']].names,stride);all_ticks+=len(result['observations'])
                selected=[]
                for key in ['confirmed_only_events','handoff_events']:
                    events=[r for r in result[key] if spec['scope_start_frame0']<=r['frame0']<spec['scope_end_exclusive']]
                    record={'scene':spec['name'],'condition':cname,'model':condition['model'],'input_size':condition['input_size'],
                        'sample_stride':stride,'nominal_inference_Hz':spec['fps']/stride,'counter':key,
                        'down':sum(r['direction']=='A->B' for r in events),'up':sum(r['direction']=='B->A' for r in events),'events':events,
                        'human_down_total':None,'absolute_down_total_error':None,'formal_event_metrics':None}
                    if spec['name']=='original':record['human_down_total']=12;record['absolute_down_total_error']=abs(record['down']-12)
                    else:record['formal_event_metrics']=evaluate_events(spec['reference_events'],events,2.)
                    selected.append(record);video_metrics.append(record)
                savegz(folder/('stride'+str(stride)+'_counter_trace.json.gz'),result)
                save(folder/('stride'+str(stride)+'_summary.json'),selected)
        print(json.dumps({'video_complete':spec['name'],'image_forwards':image_forwards,'tracker_updates':all_ticks}),flush=True)
    assert image_forwards==actual_hook_count==50700 and all_ticks==32808
    save(out/'video_metrics.json',video_metrics)
    result={'status':'ALL12_LOWRES_FROZEN_BASELINES_VALIDATION_AND_TWO_SOURCE_COUNTER_REPLAYS_COMPLETE','created_UTC':datetime.now(timezone.utc).isoformat(),
        'Slurm_JOB_ID':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/baseline_v1.json'),'model_conditions':12,
        'actual_detector_source_image_forwards':image_forwards,'predictor_inference_image_hook_count':actual_hook_count,'predictor_tensor_shapes':dict(shape_counts),
        'tracker_updates':all_ticks,'counter_paths':len(video_metrics),'prior_counter_baseline_gate':gate,
        'validation_metrics':validation_metrics,'video_metrics':video_metrics,'new_training_updates':0,'identity_encoder_forwards':0,
        'original_human12_version_changed':False,'new_independent_test':False,'board_5FPS_verified':False,'whole_goal_complete':False,
        'wall_time_s':(time.monotonic_ns()-started)/1e9,'peak_process_RSS_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    save(out/'summary.json',result)
    save(ROOT/'results/artifact_manifest.json',[{'relative_file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(out.rglob('*')) if f.is_file()])
    print(json.dumps({k:v for k,v in result.items() if k not in ['video_metrics','validation_metrics']}),flush=True)
if __name__=='__main__':main()
