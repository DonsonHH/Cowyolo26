"""Slurm-only four-checkpoint replay with the accepted native-coordinate pipeline."""
from pathlib import Path
import csv,hashlib,json,os,socket,subprocess,sys,time
import cv2,numpy as np,torch,ultralytics
from ultralytics import YOLO
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/long_video_fixed_replay_20261029')
sys.path.insert(0,str(ROOT/'input'))
from native_restore import callback,controls
from zone_counter import ZoneCounter
from confirmation_counter import ConfirmationHandoffCounter
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):p.write_text(json.dumps(value,indent=2))
def csvsave(p,rows,fields):
    with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def run(spec,p):
    out=ROOT/'results'/spec['name'];out.mkdir(parents=True,exist_ok=False)
    assert sha(spec['checkpoint'])==spec['sha256'];torch.manual_seed(26);np.random.seed(26)
    model=YOLO(spec['checkpoint']);cow=next(k for k,v in model.names.items() if v=='cow')
    raw=[];seams=[];post=[];tracks=[];observations=[];events=[];baseline_events=[];timings=[]
    holder={'image':None,'frame':0,'crop':p['crop_x']};restore=callback(holder,raw,seams);model.add_callback('on_predict_postprocess_end',restore)
    candidate=ConfirmationHandoffCounter(**p['counter']);baseline=ZoneCounter(**p['counter'])
    cap=cv2.VideoCapture(p['source_video']);assert cap.isOpened()
    assert (int(cap.get(3)),int(cap.get(4)),cap.get(5))==(2560,1440,25.)
    held=[];sample=None;first_raw=0;writer=None;window_active=None;encode_log=None;media_rows=[];media_frame_count=0
    ffmpeg='/share/home/renly/miniconda3/envs/pid310_gpu/bin/ffmpeg'
    def encode_open(w):
        folder=out/w['name'];folder.mkdir();dest=folder/'predictions.mp4';log=(folder/'encode.log').open('wb')
        cmd=[ffmpeg,'-hide_banner','-v','warning','-f','rawvideo','-pix_fmt','bgr24','-s','1280x720','-r','25','-i','pipe:0',
             '-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-threads','2','-movflags','+faststart',str(dest)]
        return subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log),log,dest
    begin=time.perf_counter();source_frames=0
    try:
        for frame in range(p['end_source_frame0_exclusive']):
            ok,image=cap.read();assert ok,(spec['name'],frame);source_frames+=1
            if frame%5==0:
                holder.update(image=image,frame=frame);tick=time.perf_counter();rotated=np.rot90(image,k=-1).copy()
                result=model.track(rotated,persist=True,tracker=p['tracker'],classes=[cow],imgsz=p['imgsz'],
                                   conf=p['confidence'],iou=p['NMS_IoU'],device=0,half=False,verbose=False)[0]
                timings.append(time.perf_counter()-tick);sample=frame;assert result.orig_shape==(1440,2560)
                if len(seams)==1:
                    functions=[getattr(c,'func',c) for c in model.predictor.callbacks['on_predict_postprocess_end']]
                    tracker_index=next(i for i,f in enumerate(functions) if f.__module__=='ultralytics.trackers.track')
                    assert functions.index(restore)<tracker_index
                assert seams[-1]['frame']==frame
                b=result.boxes;IDs=b.id.int().cpu().tolist() if b.id is not None else [None]*len(b)
                active={ID for ID in IDs if ID is not None};positions={};tentative={};held=[]
                for box,score,ID in zip(b.xyxy.cpu().tolist(),b.conf.cpu().tolist(),IDs):
                    x1,y1,x2,y2=box;row=dict(zip(['frame0','time_s','track_id','confidence','x1','y1','x2','y2'],[frame,frame/25,ID,score,*box]));post.append(row)
                    cx=(x1+x2)/5120;cy=(y1+y2)/2880
                    if ID is not None and .34<cx<.75:
                        positions[ID]=cy;item={**row,'axis_position':cy};tracks.append(item);held.append(item)
                tracker=model.predictor.trackers[0]
                for t in tracker.tracked_stracks:
                    if t.is_activated:continue
                    x1,y1,x2,y2=np.asarray(t.xyxy,np.float32).astype(float)
                    if .34<(x1+x2)/5120<.75:tentative[int(t.track_id)]=(y1+y2)/2880
                for output,target in [(baseline.update(frame/25,positions),baseline_events),
                                      (candidate.update(frame/25,positions,tentative,active),events)]:
                    for event in output:event['frame0']=frame;target.append(event)
                observations.append({'frame0':frame,'time_s':frame/25,'confirmed_positions':positions,'confirmed_IDs':sorted(active),
                                     'tentative_positions':tentative,'accepted_history':candidate.last_acceptances})
                if frame%1250==0:print(json.dumps({'model':spec['name'],'processed_source_frame0':frame,'observation_ticks':len(observations)}),flush=True)
            current=next((w for w in p['windows'] if w['start_frame0']<=frame<w['end_frame0_exclusive']),None)
            if current is not None:
                if writer is None:
                    writer,encode_log,movie=encode_open(current);window_active=current;media_frame_count=0
                assert current['name']==window_active['name']
                view=cv2.resize(image,(1280,720),interpolation=cv2.INTER_AREA)
                for x in [.34,.75]:cv2.line(view,(round(1280*x),0),(round(1280*x),719),(0,177,255),2)
                for y in [.4,.6]:cv2.line(view,(round(.34*1280),round(y*720)),(round(.75*1280),round(y*720)),(0,177,255),2)
                for row in held:
                    x1,y1,x2,y2=[round(row[k]/2) for k in ['x1','y1','x2','y2']]
                    cv2.rectangle(view,(x1,y1),(x2,y2),(109,236,151),2)
                    cv2.putText(view,f"id {row['track_id']} {row['confidence']:.2f}",(x1,max(70,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,.61,(109,236,151),2)
                window_events=[e for e in events if current['start_frame0']<=e['frame0']<current['end_frame0_exclusive']]
                down=sum(e['direction']=='A->B' for e in window_events);up=sum(e['direction']=='B->A' for e in window_events)
                cv2.rectangle(view,(0,0),(1280,60),(17,24,39),-1)
                cv2.putText(view,spec['name']+' | '+current['name']+' | original-time source',(12,25),cv2.FONT_HERSHEY_SIMPLEX,.70,(240,240,240),2)
                cv2.putText(view,f'frame0 {frame}, sample {sample} | predicted down {down}, up {up}',(12,49),cv2.FONT_HERSHEY_SIMPLEX,.64,(240,240,240),1)
                cv2.rectangle(view,(0,690),(1280,720),(17,24,39),-1)
                cv2.putText(view,'Predictions only; assistant reference pending review. Track ID is not registered cow identity.',(12,711),cv2.FONT_HERSHEY_SIMPLEX,.53,(224,224,224),1)
                writer.stdin.write(view.tobytes());media_frame_count+=1
                if frame==current['end_frame0_exclusive']-1:
                    writer.stdin.close();assert writer.wait()==0;encode_log.close();writer=None
                    assert media_frame_count==current['end_frame0_exclusive']-current['start_frame0']
                    media_rows.append({'window':current['name'],'path':movie.relative_to(ROOT).as_posix(),'sha256':sha(movie),'frames':media_frame_count,
                                       'fps':25,'dimensions':[1280,720]});window_active=None
        cap.release();assert writer is None
    except BaseException:
        cap.release()
        if writer is not None and writer.poll() is None:writer.terminate();writer.wait()
        if encode_log is not None and not encode_log.closed:encode_log.close()
        raise
    assert source_frames==10125 and len(observations)==len(seams)==len(timings)==2025 and len(media_rows)==3
    csvsave(out/'raw_detector_boxes.csv',raw,['frame','confidence','u1','v1','u2','v2','x1','y1','x2','y2'])
    fields=['frame0','time_s','track_id','confidence','x1','y1','x2','y2'];csvsave(out/'post_tracker_boxes.csv',post,fields);csvsave(out/'tracks.csv',tracks,fields+['axis_position'])
    save(out/'seam_checks.json',seams);save(out/'observations.json',observations);save(out/'handoff_events_all_history.json',events);save(out/'confirmed_only_events_all_history.json',baseline_events)
    scopes=[]
    for window in p['windows']:
        a,b=window['start_frame0'],window['end_frame0_exclusive'];raw_selected=[r for r in raw if a<=r['frame']<b];tracked_selected=[r for r in tracks if a<=r['frame0']<b]
        per_counter=[]
        for name,all_events in [('confirmed_only',baseline_events),('confirmation_handoff',events)]:
            selected=[e for e in all_events if a<=e['frame0']<b];save(out/window['name']/(name+'_events.json'),selected)
            per_counter.append({'counter':name,'predicted_down':sum(e['direction']=='A->B' for e in selected),
                                'predicted_up':sum(e['direction']=='B->A' for e in selected),'events':selected})
        scopes.append({'window':window['name'],'source_frame_range_halfopen':[a,b],'sampled_ticks':len(range(a,b,5)),
                       'raw_rows':len(raw_selected),'raw_any_box_ticks':len({r['frame'] for r in raw_selected}),
                       'raw_ROI_ticks':len({r['frame'] for r in raw_selected if .34<(r['x1']+r['x2'])/5120<.75}),
                       'tracked_ROI_rows':len(tracked_selected),'tracked_ROI_ticks':len({r['frame0'] for r in tracked_selected}),
                       'ROI_track_IDs':sorted({r['track_id'] for r in tracked_selected}),'counter_paths':per_counter})
    record={'status':'FROZEN_MODEL_NATIVE_LONG_SESSION_REPLAY_COMPLETE','model':spec['name'],'checkpoint_sha256':spec['sha256'],
            'source_sha256':p['source_sha256'],'protocol_sha256':sha(ROOT/'protocol/replay_v1.json'),'source_frames_read':source_frames,
            'model_forwards':2025,'source_history_start0':0,'raw_rows_all_history':len(raw),'tracked_ROI_rows_all_history':len(tracks),
            'restoration_seam_checks':len(seams),'maximum_inverse_error':max(r['inverse_rounding_error'] for r in seams),
            'all_scope_events':scopes,'media':media_rows,'handoff_events_all_history':len(events),'confirmed_events_all_history':len(baseline_events),
            'detector_call_seconds':timings,'server_elapsed_s':time.perf_counter()-begin,'timing_is_not_PYNQ_measurement':True,
            'formal_reference_scores_computed':False,'new_training_updates':0,'FPGA_execution_verified':False,'whole_goal_complete':False}
    save(out/'summary.json',record);print(json.dumps({k:v for k,v in record.items() if k not in ['detector_call_seconds','all_scope_events','media']}),flush=True);return record

def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';torch.set_num_threads(4);cv2.setNumThreads(2)
    p=json.loads((ROOT/'protocol/replay_v1.json').read_text());assert ultralytics.__version__==p['ultralytics']=='8.4.63' and torch.cuda.is_available()
    assert sha(p['source_video'])==p['source_sha256'];assert p['formal_accuracy_or_F1_computation_allowed'] is False
    for name,digest in p['input_module_sha256'].items():assert sha(ROOT/'input'/name)==digest
    mapping={'installed_track.py':'trackers/track.py','installed_byte_tracker.py':'trackers/byte_tracker.py','installed_bytetrack.yaml':'cfg/trackers/bytetrack.yaml'}
    for r in p['installed_source']:assert sha(Path(ultralytics.__path__[0])/mapping[r['file']])==r['sha256']
    assert sha(Path(ultralytics.__path__[0])/'trackers/utils/matching.py')==p['matching_source_sha256']
    (ROOT/'results').mkdir(exist_ok=False);save(ROOT/'results/native_restore_controls.json',controls())
    rows=[run(spec,p) for spec in p['models']];assert len(rows)==4
    summary={'status':'FOUR_FROZEN_CHECKPOINTS_LONG_VIDEO_EIGHT_COUNTER_PATHS_COMPLETE','job_id':os.environ['SLURM_JOB_ID'],
             'protocol_sha256':sha(ROOT/'protocol/replay_v1.json'),'models':rows,'models_count':4,'counter_paths':8,
             'model_forwards':sum(r['model_forwards'] for r in rows),'training_updates':0,'formal_scores_computed':False,
             'source_or_reference_labels_changed':False,'current_confirmed12_clip_changed':False,'FPGA_execution_verified':False,'whole_goal_complete':False}
    assert summary['model_forwards']==8100;save(ROOT/'results/summary.json',summary)
    manifest=[]
    for folder in [ROOT/'results',ROOT/'protocol',ROOT/'input']:
        for f in sorted(folder.rglob('*')):
            if f.is_file():manifest.append({'file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)})
    save(ROOT/'delivery_manifest.json',{'files':manifest})
    import tarfile
    archive=ROOT/'replay_delivery.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        for r in manifest:tar.add(ROOT/r['file'],arcname=r['file'])
        tar.add(ROOT/'delivery_manifest.json',arcname='delivery_manifest.json')
    print(json.dumps({'status':summary['status'],'model_forwards':8100,'files':len(manifest)+1,'archive_bytes':archive.stat().st_size,
                      'archive_sha256':sha(archive)}),flush=True)
if __name__=='__main__':main()
