"""Fixed full-scope photometric experiment; baseline must reproduce first."""
from pathlib import Path
from datetime import datetime,timezone
import os,sys,socket,json,gzip,hashlib,time,resource
os.environ['OMP_NUM_THREADS']='4'
os.environ['OPENBLAS_NUM_THREADS']='4'
sys.dont_write_bytecode=True
import cv2,numpy as np,onnxruntime as ort
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def gz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    assert not p.exists(),p
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def savegz(p,v):
    assert not p.exists(),p
    p.parent.mkdir(parents=True,exist_ok=True)
    with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write(json.dumps(v,separators=(',',':')).encode())

def restore(box,crop,rotate):
    x,y,x2,y2=crop
    a,b,c,d=box
    return [b+x,y2-c,d+x,y2-a] if rotate else [a+x,b+y,c+x,d+y]

def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    cv2.setNumThreads(1)
    p=load(ROOT/'protocol/study_v2.json')
    e=load(ROOT/'protocol/execution_v2.json')
    assert sha(ROOT/'protocol/study_v2.json')==e['protocol_sha256']
    for name,digest in e['files_sha256'].items():assert sha(ROOT/name)==digest,name
    for row in p['frozen_external_files']:assert sha(row['path'])==row['sha256'],row['path']
    sys.path[:0]=[str(PROJECT/'pynq_frontend_port_20261029'),str(ROOT/'input'),str(ROOT/'tools')]
    from frame_pipeline import FramePipeline
    from geometry import reference,assign
    from event_metrics import evaluate_events
    from photometric import preprocess,GAMMA_LUT
    from frozen_input import preprocess as old_preprocess
    sys.path.insert(0,str(PROJECT/'pynq_rot192_compile_20261029/compiler_workspace/runtime'))
    from board_runtime import decode
    started=time.monotonic_ns()
    out=ROOT/'results/study_v2'
    out.mkdir(parents=True,exist_ok=False)
    assert GAMMA_LUT.shape==(256,) and GAMMA_LUT[0]==0 and GAMMA_LUT[-1]==255
    assert np.all(np.diff(GAMMA_LUT.astype(int))>=0) and np.all(GAMMA_LUT>=np.arange(256))
    for value in [0,127,255]:
        image=np.full((45,63,3),value,np.uint8)
        for name in p['conditions']:
            x,padded,g=preprocess(image,name)
            assert x.shape==(1,3,192,192) and padded.shape==(192,192,3)
            assert np.isfinite(x).all() and x.min()>=0 and x.max()<=1
            assert np.all(padded[:g['top']]==114)
            if name=='none':assert x.tobytes()==old_preprocess(image).tobytes()
    prior=Path(p['prior_quality_remote'])
    board_inputs=load(prior/'board_input_manifest.json')
    old_input_hash={(r['scene'],r['frame0']):r['input_tensor_sha256'] for r in board_inputs}
    assert len(old_input_hash)==2654
    validation=load(ROOT/'input/validation_images.json')
    assert len(validation)==1571
    with np.load(prior/'validation_all_raw.npz') as archive:old_val={m:archive[m] for m in ['FP32','QDQ']}
    valrefs=[[reference(a)['visible_reference_AABB'] for a in row['reference_annotations']] for row in validation]
    assert sum(map(len,valrefs))==1864
    sessions={}
    forwards={name:{mode:0 for mode in ['FP32','QDQ']} for name in p['conditions']}
    all_val=[];all_video=[];all_inputs=[];anchor_rows=[];baseline_raw_exact=0;baseline_input_exact=0
    preprocess_ns={name:[] for name in p['conditions']}
    for mode in ['FP32','QDQ']:
        options=ort.SessionOptions()
        options.intra_op_num_threads=4;options.inter_op_num_threads=1
        options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_DISABLE_ALL
        sessions[mode]=ort.InferenceSession(p[mode+'_onnx'],sess_options=options,providers=['CPUExecutionProvider'])
    def infer(condition,mode,x):
        raw=sessions[mode].run(None,{'images':x})[0]
        forwards[condition][mode]+=1
        assert raw.shape==(1,300,6) and raw.dtype==np.float32 and np.isfinite(raw).all() and np.all(raw[:,:,5]==0)
        return raw[0].copy()
    def prepare(image,condition):
        t=time.monotonic_ns();x,padded,geom=preprocess(image,condition)
        preprocess_ns[condition].append(time.monotonic_ns()-t)
        return x,padded,geom
    for condition in p['conditions']:
        if condition!='none':
            gate=load(out/'baseline_gate.json')
            assert gate['baseline_raw_arrays_byte_exact']==8450 and gate['baseline_video_input_tensors_byte_exact']==2654
        dest=out/condition;dest.mkdir()
        predictions={m:[] for m in sessions};arrays={m:[] for m in sessions}
        for index,row in enumerate(validation):
            native=cv2.imread(row['image_alias'])
            assert native.shape==(720,1280,3) and sha(row['image_alias'])==row['sha256']
            image=cv2.rotate(native,cv2.ROTATE_90_CLOCKWISE)
            x,padded,geom=prepare(image,condition)
            if condition=='none':assert x.tobytes()==old_preprocess(image).tobytes()
            digest=hashlib.sha256(x.tobytes()).hexdigest()
            all_inputs.append({'condition':condition,'role':'validation','file_name':row['file_name'],'tensor_sha256':digest})
            for mode in sessions:
                raw=infer(condition,mode,x);arrays[mode].append(raw)
                if condition=='none':
                    assert raw.tobytes()==old_val[mode][index].tobytes(),('baseline_validation_raw',mode,index)
                    baseline_raw_exact+=1
                selected=decode(raw[None],image.shape,.2,192)
                boxes=[{'xyxy':restore(r[:4].astype(float).tolist(),[0,0,1280,720],True),'confidence':float(r[4]),'class':0} for r in selected]
                matches,_=assign(valrefs[index],[r['xyxy'] for r in boxes])
                predictions[mode].append({'file_name':row['file_name'],'source_sha256':row['sha256'],'reference_AABB':valrefs[index],
                    'predictions':boxes,'matches':[{'reference_index':a,'prediction_index':b,'IoU':score} for a,b,score in matches]})
            if index%500==0:print(json.dumps({'condition':condition,'validation_done':index+1,'forwards':forwards[condition]}),flush=True)
        np.savez_compressed(dest/'validation_all_raw.npz',**{m:np.stack(a) for m,a in arrays.items()})
        for mode,rows in predictions.items():
            tp=sum(len(r['matches']) for r in rows);n=sum(len(r['predictions']) for r in rows)
            all_val.append({'condition':condition,'mode':mode,'images':1571,'references':1864,'TP':tp,'unmatched_reference':1864-tp,
                'unmatched_prediction':n-tp,'recall':tp/1864,'precision_vs_reference':tp/n if n else None})
            savegz(dest/(mode+'_validation_predictions.json.gz'),rows)
        del arrays,predictions
        for video in p['videos']:
            assert sha(video['path'])==video['sha256']
            cap=cv2.VideoCapture(video['path']);assert cap.isOpened()
            x0,y0,x1,y1=video['detection_crop_xyxy'];rotated=video['orientation']=='clockwise90'
            raw_records={m:[] for m in sessions};raw_arrays={m:[] for m in sessions}
            old_raw=None
            if condition=='none':
                with np.load(prior/(video['name']+'_all_raw.npz')) as archive:old_raw={m:archive[m] for m in sessions}
            frame_index=0;controls=set(video['pixel_control_frames'])
            if video['name']=='original':controls.update([9310,9345,9360])
            for frame in range(video['decode_end_exclusive']):
                ok,native=cap.read();assert ok and native.shape==(video['height'],video['width'],3)
                if frame%video['inference_stride']:continue
                image=native[y0:y1,x0:x1].copy()
                if rotated:image=cv2.rotate(image,cv2.ROTATE_90_CLOCKWISE)
                x,padded,geom=prepare(image,condition)
                digest=hashlib.sha256(x.tobytes()).hexdigest()
                if condition=='none':
                    assert digest==old_input_hash[video['name'],frame],(video['name'],frame)
                    baseline_input_exact+=1
                all_inputs.append({'condition':condition,'role':video['name'],'frame0':frame,'tensor_sha256':digest})
                for mode in sessions:
                    raw=infer(condition,mode,x);raw_arrays[mode].append(raw)
                    if condition=='none':
                        assert raw.tobytes()==old_raw[mode][frame_index].tobytes(),('baseline_video_raw',video['name'],mode,frame)
                        baseline_raw_exact+=1
                    selected=decode(raw[None],image.shape,.2,192)
                    boxes=[{'crop_oriented_xyxy':r[:4].astype(float).tolist(),'xyxy':restore(r[:4].astype(float).tolist(),video['detection_crop_xyxy'],rotated),
                        'confidence':float(r[4]),'class':0} for r in selected]
                    raw_records[mode].append({'frame0':frame,'time_s':frame/video['fps'],'predictions':boxes})
                if frame in controls:
                    name=condition+'_'+video['name']+'_f'+str(frame)
                    pixel=out/'pixel_controls'/(name+'.png');pixel.parent.mkdir(exist_ok=True)
                    assert cv2.imwrite(str(pixel),padded)
                    arrayfile=out/'pixel_controls'/(name+'.npz')
                    np.savez_compressed(arrayfile,input=x,**{m:raw_arrays[m][-1] for m in sessions})
                    anchor_rows.append({'condition':condition,'scene':video['name'],'frame0':frame,'geometry':geom,'tensor_sha256':digest,
                        'pixel_file':pixel.relative_to(out).as_posix(),'pixel_sha256':sha(pixel),'array_file':arrayfile.relative_to(out).as_posix(),'array_sha256':sha(arrayfile)})
                frame_index+=1
            cap.release()
            del old_raw
            scene=dest/video['name'];scene.mkdir()
            np.savez_compressed(dest/(video['name']+'_all_raw.npz'),**{m:np.stack(a) for m,a in raw_arrays.items()})
            for mode,rows in raw_records.items():
                md=scene/mode;md.mkdir();savegz(md/'raw_predictions.json.gz',rows)
                if condition=='none':assert rows==gz(prior/video['name']/mode/'raw_predictions.json.gz')
                byframe={r['frame0']:r['predictions'] for r in rows}
                for stride in video['counter_replay_strides']:
                    pipeline=FramePipeline(video,p['tracker_config'],p['counter_kwargs'])
                    trace={'observations':[],'post_tracker':[],'confirmed_only_events':[],'handoff_events':[]}
                    for frame in range(0,video['decode_end_exclusive'],stride):
                        result=pipeline.update(frame,byframe[frame]);trace['observations'].append(result['observation'])
                        for key in ['post_tracker','confirmed_only_events','handoff_events']:trace[key].extend(result[key])
                    if condition=='none':assert json.loads(json.dumps(trace))==gz(prior/video['name']/mode/('stride'+str(stride)+'_counter_trace.json.gz'))
                    savegz(md/('stride'+str(stride)+'_counter_trace.json.gz'),trace)
                    for counter in ['confirmed_only_events','handoff_events']:
                        events=[r for r in trace[counter] if video['scope_start_frame0']<=r['frame0']<video['scope_end_exclusive']]
                        all_video.append({'condition':condition,'scene':video['name'],'mode':mode,'stride':stride,'counter':counter,
                            'down':sum(r['direction']=='A->B' for r in events),'up':sum(r['direction']=='B->A' for r in events),'events':events,
                            'formal_event_metrics':evaluate_events(video['reference_events'],events,2.) if video['name']=='toros' else None})
            print(json.dumps({'condition':condition,'scene_complete':video['name'],'image_forwards':forwards[condition]}),flush=True)
        if condition=='none':
            assert baseline_raw_exact==8450 and baseline_input_exact==2654
            save(out/'baseline_gate.json',{'status':'ALL8450_BASELINE_RAW_ARRAYS_AND2654_VIDEO_INPUTS_AND6_TRACKER_TRACES_EXACT',
                'baseline_raw_arrays_byte_exact':baseline_raw_exact,'baseline_video_input_tensors_byte_exact':baseline_input_exact,
                'baseline_full_tracker_traces_exact':6,'new_transform_forwards_at_gate':0})
    del old_val
    assert forwards=={c:{'FP32':4225,'QDQ':4225} for c in p['conditions']}
    assert len(all_inputs)==12675 and len(all_val)==6 and len(all_video)==36 and len(anchor_rows)==30
    save(out/'input_hashes.json',all_inputs);save(out/'pixel_controls.json',anchor_rows)
    save(out/'validation_metrics.json',all_val);save(out/'video_metrics.json',all_video)
    prep={c:{'count':len(a),'mean_ms':float(np.mean(a))/1e6,'P95_ms':float(np.percentile(a,95))/1e6,
        'scope':'server_CPU_resize_transform_letterbox_tensor_not_PYNQ'} for c,a in preprocess_ns.items()}
    summary={'status':'THREE_FIXED_PHOTOMETRIC_CONDITIONS25350_REAL_ORT_FORWARDS_COMPLETE','created_UTC':datetime.now(timezone.utc).isoformat(),
        'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/study_v2.json'),'actual_ORT_forwards':forwards,
        'actual_total_forwards':sum(sum(a.values()) for a in forwards.values()),'baseline_raw_arrays_exact':baseline_raw_exact,
        'baseline_video_inputs_exact':baseline_input_exact,'validation_metrics':all_val,'video_metrics':all_video,'preprocessing_server_only':prep,
        'counter_paths':36,'tracker_observation_ticks':16404,'new_training_updates':0,'new_independent_test':False,'actual_board_actions':0,
        'model_calibration_counter_or_firmware_changed':False,'adopted_for_deployment':False,'whole_goal_complete':False,
        'wall_s':(time.monotonic_ns()-started)/1e9,'peak_RSS_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'package_versions':{'numpy':np.__version__,'opencv':cv2.__version__,'onnxruntime':ort.__version__}}
    save(out/'summary.json',summary)
    save(ROOT/'results/artifact_manifest.json',[{'file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(out.rglob('*')) if f.is_file()])
    print(json.dumps({k:v for k,v in summary.items() if k not in ['video_metrics']}),flush=True)
if __name__=='__main__':main()
