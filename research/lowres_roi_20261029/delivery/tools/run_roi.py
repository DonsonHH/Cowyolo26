"""Fixed physical-lane cropping only; all models/sizes/native counters unchanged."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import os,sys,socket,json,hashlib,gzip,time,resource,importlib.util
import numpy as np,cv2,torch,ultralytics
from ultralytics import YOLO
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text())
def loadgz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(p,v):assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def savegz(p,v):
    assert not p.exists(),p
    with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write(json.dumps(v,separators=(',',':')).encode())
def restore(box,crop,rotate):
    x0,y0,x2,y2=crop;h=y2-y0;u1,v1,u2,v2=box
    return [v1+x0,h-u2+y0,v2+x0,h-u1+y0] if rotate else [u1+x0,v1+y0,u2+x0,v2+y0]
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01' and torch.cuda.is_available()
    assert ultralytics.__version__=='8.4.63';cv2.setNumThreads(1);torch.set_num_threads(4)
    protocol=load(ROOT/'protocol/roi_v1.json');baseline=Path(protocol['baseline_root_remote'])
    assert sha(baseline/'protocol/baseline_v2_path_fix.json')==protocol['baseline_protocol_sha256']
    assert sha(baseline/'results/baseline/summary.json')==protocol['baseline_summary_sha256']
    assert sha(Path(protocol['baseline_counter_module_path']))==protocol['baseline_counter_module_sha256']
    for name,digest in protocol['input_module_sha256'].items():assert sha(ROOT/'input'/name)==digest
    for row in protocol['baseline_files']:assert sha(baseline/row['relative'])==row['sha256']
    sys.path[:0]=[str(baseline/'tools'),str(baseline/'input')]
    import run_baseline_v2 as prior
    prior.protocol=load(baseline/'protocol/baseline_v2_path_fix.json')
    assert prior.protocol['counter_kwargs']==protocol['counter_kwargs'] and prior.protocol['prediction']==protocol['prediction']
    out=ROOT/'results/roi';out.mkdir(parents=True,exist_ok=False);pixel=out/'pixel_controls';pixel.mkdir()
    toy=np.arange(6*10*3,dtype=np.uint8).reshape(6,10,3);croptoy=toy[1:6,2:8]
    assert np.array_equal(np.rot90(np.rot90(croptoy,k=-1),k=1),croptoy)
    assert restore([1,1,4,5],[2,1,8,6],True)==[3,2,7,5]
    assert restore([1,1,5,4],[2,1,8,6],False)==[3,2,7,5]
    models={};forwards=hookcount=0;shapes=Counter();tensor_rows=[];pixel_rows=[];active={};saved_tensors=set();started=time.monotonic_ns()
    def onstart(predictor):
        if getattr(predictor,'_roi_hooked',False):return
        previous=predictor.inference
        def inference(im,*args,**kwargs):
            nonlocal hookcount
            assert len(im)==len(active['metadata']);hookcount+=len(im);shapes[str(tuple(im.shape))]+=1
            for j,meta in enumerate(active['metadata']):
                if meta['frame0'] not in active['spec']['pixel_control_frames']:continue
                array=im[j].detach().cpu().contiguous().numpy();size=active['condition']['input_size']
                identity=(active['spec']['name'],meta['frame0'],size);digest=hashlib.sha256(array.tobytes()).hexdigest()
                tensor_rows.append({'scene':identity[0],'frame0':identity[1],'input_size':size,'condition':active['condition']['condition'],
                'tensor_sha256':digest,'shape':list(array.shape)})
                if identity not in saved_tensors:
                    path=pixel/(identity[0]+'_f'+str(identity[1])+'_s'+str(size)+'_NN.npz');np.savez_compressed(path,actual_input=array)
                    saved_tensors.add(identity)
            return previous(im,*args,**kwargs)
        predictor.inference=inference;predictor._roi_hooked=True
    for m in protocol['models']:
        assert sha(Path(m['checkpoint']))==m['sha256'];model=YOLO(m['checkpoint']);model.add_callback('on_predict_start',onstart);models[m['name']]=model
    reg=[];regticks=0
    for spec in protocol['videos']:
        for condition in protocol['conditions']:
            cname=condition['condition'];folder=baseline/'results/baseline'/spec['name']/cname;raw=loadgz(folder/'raw_predictions.json.gz')
            for stride in spec['counter_replay_strides']:
                actual=prior.counter_replay(spec,raw,models[condition['model']].names,stride);expected=loadgz(folder/('stride'+str(stride)+'_counter_trace.json.gz'))
                assert json.loads(json.dumps(actual))==expected,(spec['name'],cname,stride)
                regticks+=len(actual['observations'])
                reg.append({'scene':spec['name'],'condition':cname,'stride':stride,'observation_ticks':len(actual['observations']),'entire_trace_exact':True})
    assert regticks==32808 and len(reg)==36
    save(out/'full_input_cache_regression_gate.json',{'status':'ALL36_FULLINPUT_TRACES_AND72_COUNTER_EVENT_LISTS_EXACT_BEFORE_ROI_FORWARD','tracker_updates':regticks,'traces':reg,
    'pixel_permutation_toy_exact':True,'inverse_coordinate_toys_exact':True,'new_model_forwards_at_gate':0})
    all_metrics=[];crop_ticks=0;source_metadata=[]
    for spec in protocol['videos']:
        assert sha(Path(spec['path']))==spec['sha256'];cap=cv2.VideoCapture(spec['path']);assert cap.isOpened()
        x0,y0,x1,y1=spec['detection_crop_xyxy'];h=y1-y0;w=x1-x0;rotate=spec['orientation']=='clockwise90'
        raw={c['condition']:[] for c in protocol['conditions']};batch=[];metadata=[];decoded=0;controls=[]
        def flush():
            nonlocal forwards
            if not batch:return
            for c in protocol['conditions']:
                active.update({'spec':spec,'condition':c,'metadata':metadata})
                model=models[c['model']];cow=next(k for k,v in model.names.items() if v=='cow')
                outputs=model.predict(batch,imgsz=c['input_size'],rect=False,batch=16,conf=.2,iou=.5,classes=[cow],max_det=300,half=False,augment=False,device=0,verbose=False)
                assert len(outputs)==len(batch);forwards+=len(batch)
                for result,meta in zip(outputs,metadata):
                    assert result.orig_shape==((w,h) if rotate else (h,w))
                    boxes=result.boxes.xyxy.detach().cpu().numpy().astype(float).tolist();scores=result.boxes.conf.detach().cpu().numpy().astype(float).tolist()
                    predictions=[{'crop_oriented_xyxy':box,'xyxy':restore(box,spec['detection_crop_xyxy'],rotate),'confidence':score,'class':cow} for box,score in zip(boxes,scores)]
                    assert all(x0-1e-4<=r['xyxy'][0]<=r['xyxy'][2]<=x1+1e-4 and y0-1e-4<=r['xyxy'][1]<=r['xyxy'][3]<=y1+1e-4 for r in predictions)
                    raw[c['condition']].append({**meta,'predictions':predictions})
            batch.clear();metadata.clear()
        for frame in range(spec['decode_end_exclusive']):
            ok,native=cap.read();assert ok and native.shape==(spec['height'],spec['width'],3);decoded+=1
            if frame%spec['inference_stride']:continue
            crop=native[y0:y1,x0:x1].copy();assert crop.shape==(h,w,3)
            image=np.rot90(crop,k=-1).copy() if rotate else crop
            if frame in spec['pixel_control_frames']:
                path=pixel/(spec['name']+'_f'+str(frame)+'_crop_native.png');assert cv2.imwrite(str(path),crop)
                context=pixel/(spec['name']+'_f'+str(frame)+'_context.jpg');cv2.imwrite(str(context),cv2.resize(native,(1280,720),interpolation=cv2.INTER_AREA),[cv2.IMWRITE_JPEG_QUALITY,95])
                controls.append({'scene':spec['name'],'frame0':frame,'source_SHA256':spec['sha256'],'crop_box':spec['detection_crop_xyxy'],
                'source_decoded_RGB_pixel_sha256':hashlib.sha256(native[:,:,::-1].copy().tobytes()).hexdigest(),
                'crop_native_RGB_pixel_sha256':hashlib.sha256(crop[:,:,::-1].copy().tobytes()).hexdigest(),
                'crop_oriented_RGB_pixel_sha256':hashlib.sha256(image[:,:,::-1].copy().tobytes()).hexdigest(),
                'crop_native_file':path.relative_to(ROOT).as_posix(),'crop_native_file_SHA256':sha(path),'context_file':context.relative_to(ROOT).as_posix(),
                'context_file_SHA256':sha(context),'source_native_dimensions_WH':[spec['width'],spec['height']]})
            batch.append(image);metadata.append({'frame0':frame,'time_s':frame/spec['fps']})
            if len(batch)==16:flush()
            if frame%2500==0:print(json.dumps({'scene':spec['name'],'decoded_frame0':frame,'source_image_forwards':forwards}),flush=True)
        flush();cap.release();assert decoded==spec['decode_end_exclusive'] and len(controls)==4
        pixel_rows.extend(controls);source_metadata.append({'scene':spec['name'],'decoded_frames':decoded,'sampled_frames':len(next(iter(raw.values()))),'crop_box':spec['detection_crop_xyxy']})
        for c in protocol['conditions']:
            cname=c['condition'];folder=out/spec['name']/cname;folder.mkdir(parents=True,exist_ok=False);savegz(folder/'raw_predictions.json.gz',raw[cname])
            for stride in spec['counter_replay_strides']:
                trace=prior.counter_replay(spec,raw[cname],models[c['model']].names,stride);crop_ticks+=len(trace['observations']);metrics=[]
                for kind in ['confirmed_only_events','handoff_events']:
                    events=[e for e in trace[kind] if spec['scope_start_frame0']<=e['frame0']<spec['scope_end_exclusive']]
                    row={'scene':spec['name'],'condition':cname,'model':c['model'],'input_size':c['input_size'],'sample_stride':stride,
                    'nominal_inference_Hz':spec['fps']/stride,'counter':kind,'down':sum(e['direction']=='A->B' for e in events),
                    'up':sum(e['direction']=='B->A' for e in events),'events':events,'human_down_total':None,'absolute_down_total_error':None,'formal_event_metrics':None}
                    if spec['name']=='original':row['human_down_total']=12;row['absolute_down_total_error']=abs(row['down']-12)
                    else:row['formal_event_metrics']=prior.evaluate_events(spec['reference_events'],events,2.)
                    metrics.append(row);all_metrics.append(row)
                savegz(folder/('stride'+str(stride)+'_counter_trace.json.gz'),trace);save(folder/('stride'+str(stride)+'_summary.json'),metrics)
        print(json.dumps({'scene_complete':spec['name'],'image_forwards':forwards,'crop_tracker_updates':crop_ticks}),flush=True)
    assert forwards==hookcount==31848 and crop_ticks==32808 and len(tensor_rows)==96 and len(saved_tensors)==24 and len(pixel_rows)==8 and len(all_metrics)==72
    save(out/'input_tensor_controls.json',tensor_rows);save(out/'pixel_controls.json',pixel_rows);save(out/'source_decode.json',source_metadata);save(out/'video_metrics.json',all_metrics)
    paired=[];old_metrics=load(baseline/'results/baseline/video_metrics.json')
    for r in all_metrics:
        old=next(x for x in old_metrics if all(x[k]==r[k] for k in ['scene','condition','sample_stride','counter']))
        paired.append({'scene':r['scene'],'condition':r['condition'],'input_size':r['input_size'],'sample_stride':r['sample_stride'],'counter':r['counter'],
        'full_down':old['down'],'crop_down':r['down'],'full_up':old['up'],'crop_up':r['up'],
        'full_TP_FP_FN':[old['formal_event_metrics'][k] for k in ['TP','FP','FN']] if old['formal_event_metrics'] else None,
        'crop_TP_FP_FN':[r['formal_event_metrics'][k] for k in ['TP','FP','FN']] if r['formal_event_metrics'] else None})
    save(out/'paired_full_vs_roi.json',paired)
    summary={'status':'ALL12_FIXED_CHANNEL_INPUT_CONDITIONS_AND72_COUNTER_PATHS_COMPLETE','created_UTC':datetime.now(timezone.utc).isoformat(),
    'Slurm_JOB_ID':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/roi_v1.json'),'condition_count':12,
    'actual_detector_source_image_forwards':forwards,'active_predictor_inference_image_calls':hookcount,'predictor_tensor_shape_counts':dict(shapes),
    'baseline_full_cache_traces_exact':36,'baseline_full_cache_counter_paths_exact':72,'baseline_full_tracker_updates_replayed':regticks,
    'new_crop_tracker_updates':crop_ticks,'new_crop_counter_paths':72,'NN_input_anchor_hash_rows':len(tensor_rows),'unique_NN_input_arrays':len(saved_tensors),
    'source_crop_anchor_images':8,'video_metrics':all_metrics,'paired_full_vs_roi':paired,'source_decode':source_metadata,
    'new_training_updates':0,'identity_encoder_forwards':0,'new_reference_labels':0,'new_independent_test':False,'global_pipeline_changed':False,
    'board_actions_in_this_experiment':0,'PYNQ5FPS_proven':False,'whole_goal_complete':False,
    'wall_s':(time.monotonic_ns()-started)/1e9,'peak_process_RSS_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    save(out/'summary.json',summary);save(ROOT/'results/artifact_manifest.json',[{'relative_file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(out.rglob('*')) if f.is_file()])
    print(json.dumps({k:v for k,v in summary.items() if k not in ['video_metrics','paired_full_vs_roi']}),flush=True)
if __name__=='__main__':main()
