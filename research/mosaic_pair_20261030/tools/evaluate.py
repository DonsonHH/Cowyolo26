"""Freeze allsix last checkpoints, regress old traces, then evaluate every seed."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import os,sys,socket,json,gzip,time,hashlib
import numpy as np,cv2,torch,ultralytics
from ultralytics import YOLO
from common import ROOT,sha,save_new
PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text())
def gz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def savegz(p,v):
    assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True)
    with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write(json.dumps(v,separators=(',',':')).encode())
def restore(box,crop,rotate):
    a,b,c,d=box;x,y,x2,y2=crop
    return [b+x,y2-c,d+x,y2-a] if rotate else [a+x,b+y,c+x,d+y]

def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01' and torch.cuda.is_available()
    cv2.setNumThreads(1);torch.set_num_threads(4)
    p=load(ROOT/'protocol/evaluation_v1.json');e=load(ROOT/'protocol/evaluation_execution_v1.json')
    assert e['protocol_sha256']==sha(ROOT/'protocol/evaluation_v1.json')
    for file,digest in e['files_sha256'].items():assert sha(ROOT/file)==digest,file
    assert torch.__version__=='2.8.0+cu128' and ultralytics.__version__=='8.4.63'
    out=ROOT/'results/evaluation';out.mkdir(parents=True,exist_ok=False)
    training=load(ROOT/'protocol/training_v1.json');frozen=[]
    for c in training['conditions']:
        folder=ROOT/'results/training'/c['name'];s=load(folder/'condition_complete.json')
        assert s['condition']==c and s['training_batches']==2130 and s['optimizer_updates']==1225
        assert s['actual_persisted_batch_rows']==2130 and s['actual_persisted_gradient_rows']==1225
        assert s['initial_state_digest']==training['expected_initial_state_digests'][str(c['seed'])]
        last=folder/'weights/last.pt';assert sha(last)==s['last_checkpoint_sha256']
        assert sha(folder/'actual_batches.jsonl')==s['batch_audit_sha256'] and sha(folder/'actual_gradient_updates.jsonl')==s['gradient_audit_sha256']
        frozen.append({'condition':c,'checkpoint':str(last),'sha256':sha(last),'condition_complete_sha256':sha(folder/'condition_complete.json')})
    assert len(frozen)==6
    for seed in [26,27,28]:
        schedules=[load(ROOT/'results/training'/(arm+'_seed'+str(seed))/'optimizer_step_batch_indices.json') for arm in ['mosaic100','mosaic050']]
        assert len(schedules[0])==len(schedules[1])==1225 and schedules[0]==schedules[1]
    save_new(ROOT/'results/all_six_checkpoints_frozen.json',{'created_UTC':datetime.now(timezone.utc).isoformat(),'models':frozen,
        'all6_weights_frozen_before_new_source_image_forward':True,'actual_training_updates':7350,'source_image_forwards_at_freeze':0,'whole_goal_complete':False})
    port=PROJECT/'pynq_frontend_port_20261029';sys.path[:0]=[str(port),str(ROOT/'input')]
    from frame_pipeline import FramePipeline
    from geometry import reference,assign
    from event_metrics import evaluate_events
    for row in p['port_files']:assert sha(port/row['file'])==row['sha256']
    regression=0;regticks=0
    for spec in p['videos']:
        for seed in [26,27,28]:
            name='S192_rot90_seed'+str(seed)
            folder=PROJECT/'factorial_lane_crop_20261029/results/roi'/spec['name']/name
            old=gz(folder/'raw_predictions.json.gz');byframe={r['frame0']:r['predictions'] for r in old}
            for stride in spec['counter_replay_strides']:
                pipe=FramePipeline(spec,p['tracker_config'],p['counter_kwargs'])
                trace={'observations':[],'post_tracker':[],'confirmed_only_events':[],'handoff_events':[]}
                for frame in range(0,spec['decode_end_exclusive'],stride):
                    row=pipe.update(frame,byframe[frame]);trace['observations'].append(row['observation'])
                    for key in ['post_tracker','confirmed_only_events','handoff_events']:trace[key].extend(row[key])
                assert json.loads(json.dumps(trace))==gz(folder/('stride'+str(stride)+'_counter_trace.json.gz'))
                regression+=1;regticks+=len(trace['observations'])
    assert regression==9 and regticks==8202
    save_new(out/'counter_regression_gate.json',{'entire_old_traces_exact':9,'old_counter_paths_exact':18,'ticks':8202,'new_source_image_forwards':0})
    models={};active={};hook_forwards=0;anchors=[];contracts=[];forward_counts=Counter();outputs={}
    def on_predict_start(predictor):
        if getattr(predictor,'_mosaic_hooked',False):return
        previous=predictor.inference
        def inference(im,*args,**kwargs):
            nonlocal hook_forwards
            assert len(im)==len(active['metadata']) and tuple(im.shape[1:])==(3,192,192) and im.dtype==torch.float32
            result=previous(im,*args,**kwargs)
            raw=result if isinstance(result,torch.Tensor) else result[0]
            assert isinstance(raw,torch.Tensor) and raw.shape==(len(im),300,6),str(type(raw))+' '+str(getattr(raw,'shape',None))
            array=raw.detach().cpu().contiguous().numpy();assert array.dtype==np.float32 and np.isfinite(array).all() and np.all(array[:,:,5]==0)
            outputs['raw']=array.copy();hook_forwards+=len(im);forward_counts[active['condition']]+=len(im)
            for i,meta in enumerate(active['metadata']):
                if 'frame0' not in meta or meta['frame0'] not in active['spec']['pixel_control_frames']:continue
                tensor=im[i].detach().cpu().contiguous().numpy();digest=hashlib.sha256(tensor.tobytes()).hexdigest()
                key=active['spec']['name']+'_f'+str(meta['frame0'])+'_s192'
                assert digest==p['expected_NN_input_hashes'][key],key
                anchors.append({'condition':active['condition'],'scene':active['spec']['name'],'frame0':meta['frame0'],'tensor_sha256':digest})
            return result
        predictor.inference=inference;predictor._mosaic_hooked=True
    for row in frozen:
        model=YOLO(row['checkpoint']);assert model.names=={0:'cow'}
        model.add_callback('on_predict_start',on_predict_start);models[row['condition']['name']]=model
    def infer(c,images,metadata,spec):
        active.update({'condition':c,'metadata':metadata,'spec':spec});outputs.clear()
        results=models[c].predict(images,imgsz=192,rect=False,batch=16,conf=.2,iou=.5,classes=[0],max_det=300,half=False,augment=False,device=0,verbose=False)
        assert len(results)==len(metadata) and outputs['raw'].shape==(len(metadata),300,6)
        return results,outputs['raw']
    started=time.monotonic_ns();val=load(ROOT/'input/validation_images.json');assert len(val)==1571
    refs=[[reference(a)['visible_reference_AABB'] for a in row['reference_annotations']] for row in val];assert sum(map(len,refs))==1864
    val_metrics=[];video_metrics=[]
    for c in models:
        rows=[];raws=[]
        for start in range(0,len(val),16):
            batch=val[start:start+16];images=[]
            for r in batch:
                assert sha(r['image_alias'])==r['sha256'];native=cv2.imread(r['image_alias']);assert native.shape==(720,1280,3)
                images.append(cv2.rotate(native,cv2.ROTATE_90_CLOCKWISE))
            results,raw=infer(c,images,[{'file_name':r['file_name']} for r in batch],None);raws.extend(raw.copy())
            for j,(r,result) in enumerate(zip(batch,results)):
                boxes=result.boxes.xyxy.detach().cpu().numpy().astype(float).tolist();scores=result.boxes.conf.detach().cpu().numpy().astype(float).tolist()
                pred=[{'xyxy':restore(box,[0,0,1280,720],True),'confidence':score,'class':0} for box,score in zip(boxes,scores)]
                matched,_=assign(refs[start+j],[a['xyxy'] for a in pred])
                rows.append({'file_name':r['file_name'],'source_sha256':r['sha256'],'reference_AABB':refs[start+j],'predictions':pred,
                    'matches':[{'reference_index':a,'prediction_index':b,'IoU':iou} for a,b,iou in matched]})
        folder=out/c;folder.mkdir();savegz(folder/'validation_predictions.json.gz',rows)
        np.savez_compressed(folder/'validation_all_raw.npz',raw=np.stack(raws))
        tp=sum(len(r['matches']) for r in rows);n=sum(len(r['predictions']) for r in rows)
        val_metrics.append({'condition':c,'images':1571,'references':1864,'TP':tp,'unmatched_reference':1864-tp,'unmatched_prediction':n-tp})
        print(json.dumps({'validation_complete':c,'source_image_forwards':dict(forward_counts)}),flush=True)
    observation_ticks=0
    for spec in p['videos']:
        assert sha(spec['path'])==spec['sha256'];cap=cv2.VideoCapture(spec['path']);assert cap.isOpened()
        x0,y0,x1,y1=spec['detection_crop_xyxy'];rotate=spec['orientation']=='clockwise90'
        predictions={c:[] for c in models};raws={c:[] for c in models};batch=[];metadata=[]
        def flush():
            if not batch:return
            for c in models:
                results,raw=infer(c,batch,metadata,spec);raws[c].extend(raw.copy())
                for meta,result in zip(metadata,results):
                    boxes=result.boxes.xyxy.detach().cpu().numpy().astype(float).tolist();scores=result.boxes.conf.detach().cpu().numpy().astype(float).tolist()
                    pred=[{'crop_oriented_xyxy':box,'xyxy':restore(box,spec['detection_crop_xyxy'],rotate),'confidence':score,'class':0} for box,score in zip(boxes,scores)]
                    predictions[c].append({**meta,'predictions':pred})
            batch.clear();metadata.clear()
        for frame in range(spec['decode_end_exclusive']):
            ok,native=cap.read();assert ok and native.shape==(spec['height'],spec['width'],3)
            if frame%spec['inference_stride']:continue
            image=native[y0:y1,x0:x1].copy()
            if rotate:image=cv2.rotate(image,cv2.ROTATE_90_CLOCKWISE)
            batch.append(image);metadata.append({'frame0':frame,'time_s':frame/spec['fps']})
            if len(batch)==16:flush()
        flush();cap.release()
        for c,rows in predictions.items():
            folder=out/c/spec['name'];folder.mkdir();savegz(folder/'raw_predictions.json.gz',rows)
            np.savez_compressed(folder/'all_raw.npz',raw=np.stack(raws[c]));byframe={r['frame0']:r['predictions'] for r in rows}
            for stride in spec['counter_replay_strides']:
                pipe=FramePipeline(spec,p['tracker_config'],p['counter_kwargs']);trace={'observations':[],'post_tracker':[],'confirmed_only_events':[],'handoff_events':[]}
                for frame in range(0,spec['decode_end_exclusive'],stride):
                    row=pipe.update(frame,byframe[frame]);trace['observations'].append(row['observation'])
                    for key in ['post_tracker','confirmed_only_events','handoff_events']:trace[key].extend(row[key])
                observation_ticks+=len(trace['observations']);savegz(folder/('stride'+str(stride)+'_counter_trace.json.gz'),trace)
                for kind in ['confirmed_only_events','handoff_events']:
                    events=[r for r in trace[kind] if spec['scope_start_frame0']<=r['frame0']<spec['scope_end_exclusive']]
                    video_metrics.append({'condition':c,'scene':spec['name'],'stride':stride,'counter':kind,
                        'down':sum(r['direction']=='A->B' for r in events),'up':sum(r['direction']=='B->A' for r in events),'events':events,
                        'formal_event_metrics':evaluate_events(spec['reference_events'],events,2.) if spec['name']=='toros' else None})
        print(json.dumps({'scene_complete':spec['name'],'source_image_forwards':dict(forward_counts)}),flush=True)
    assert hook_forwards==25350 and dict(forward_counts)=={c:4225 for c in models} and len(anchors)==48 and observation_ticks==16404 and len(video_metrics)==36
    for row in frozen:assert sha(row['checkpoint'])==row['sha256']
    save_new(out/'input_tensor_anchors.json',anchors);save_new(out/'validation_metrics.json',val_metrics);save_new(out/'video_metrics.json',video_metrics)
    summary={'status':'ALL6_FROZEN_MOSAIC_MODELS25350_IMAGE_FORWARDS_AND36_COUNTER_PATHS_COMPLETE','created_UTC':datetime.now(timezone.utc).isoformat(),
        'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/evaluation_v1.json'),'all_six_freeze_sha256':sha(ROOT/'results/all_six_checkpoints_frozen.json'),
        'actual_source_image_forwards':hook_forwards,'actual_inference_hook_image_calls':hook_forwards,'source_image_forwards_by_model':dict(forward_counts),
        'counter_observation_ticks':observation_ticks,'counter_paths':36,'old_baseline_full_traces_exact':9,'old_baseline_regression_ticks':8202,
        'actual_NN_input_anchor_hashes_exact':48,'validation_metrics':val_metrics,'video_metrics':video_metrics,
        'new_training_updates_in_evaluation':0,'new_independent_test':False,'actual_board_actions':0,'whole_goal_complete':False,
        'wall_s':(time.monotonic_ns()-started)/1e9}
    save_new(out/'summary.json',summary)
    save_new(ROOT/'results/evaluation_manifest.json',[{'file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(out.rglob('*')) if f.is_file()])
    print(json.dumps({k:v for k,v in summary.items() if k!='video_metrics'}),flush=True)
if __name__=='__main__':main()
