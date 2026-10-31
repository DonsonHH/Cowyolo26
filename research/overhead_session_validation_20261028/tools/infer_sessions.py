"""Fixed two-model, four-session inference after camera-only calibration is frozen."""
from pathlib import Path
import csv,hashlib,json,os,socket,subprocess,sys,time
import cv2,numpy as np,torch,ultralytics
from ultralytics import YOLO
from ultralytics.trackers.byte_tracker import BYTETracker
from ultralytics.utils import YAML,IterableSimpleNamespace

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/overhead_session_validation_20261028')
sys.path.insert(0,str(ROOT/'input'))
from confirmation_counter import ConfirmationHandoffCounter
from zone_counter import ZoneCounter
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):p.write_text(json.dumps(value,indent=2))
def csvsave(p,rows,fields):
    with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def run(model,p,clip,dest):
    dest.mkdir(parents=True,exist_ok=False);cfg=YAML.load(ultralytics.__path__[0]+'/cfg/trackers/bytetrack.yaml')
    tracker=BYTETracker(IterableSimpleNamespace(**cfg));counter=ConfirmationHandoffCounter(**p['counter'])
    baseline=ZoneCounter(**p['counter']);camera=p['camera'];assert camera['rotation_degrees']==0
    cow=next(k for k,v in model.names.items() if v=='cow');cap=cv2.VideoCapture(clip['source_path']);assert cap.isOpened()
    w,h=clip['width'],clip['height'];fps=clip['fps'];stride=round(fps/p['observation_hz']);assert fps/stride==p['observation_hz']
    ffmpeg='/share/home/renly/miniconda3/envs/pid310_gpu/bin/ffmpeg';movie=dest/'predictions.mp4'
    cmd=[ffmpeg,'-hide_banner','-v','warning','-f','rawvideo','-pix_fmt','bgr24','-s',f'{w}x{h}','-r',str(fps),'-i','pipe:0',
         '-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-threads','2','-movflags','+faststart',str(movie)]
    raw=[];post=[];tracked=[];trace=[];events=[];plain=[];held=[];frame=0;sample=None;times=[]
    with (dest/'encode.log').open('wb') as log:
        writer=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log)
        try:
            while True:
                ok,image=cap.read()
                if not ok:break
                assert image.shape==(h,w,3)
                if frame%stride==0:
                    begin=time.perf_counter()
                    r=model.predict(image,imgsz=p['imgsz'],conf=p['detector_confidence'],iou=p['NMS_IoU'],classes=[cow],device=0,half=False,verbose=False)[0]
                    times.append(time.perf_counter()-begin);assert r.orig_shape==(h,w)
                    for box,score in zip(r.boxes.xyxy.cpu().tolist(),r.boxes.conf.cpu().tolist()):
                        raw.append(dict(zip(['frame0','time_s','confidence','x1','y1','x2','y2'],[frame,frame/fps,score,*box])))
                    output=tracker.update(r.boxes.cpu().numpy(),r.orig_img,feats=None)
                    if len(output):r=r[output[:,-1].astype(int)];r.update(boxes=torch.as_tensor(output[:,:-1]))
                    b=r.boxes;ids=b.id.int().cpu().tolist() if b.id is not None else [None]*len(b)
                    active={ID for ID in ids if ID is not None};positions={};tentative={};held=[]
                    for box,score,ID in zip(b.xyxy.cpu().tolist(),b.conf.cpu().tolist(),ids):
                        x1,y1,x2,y2=box;cx=(x1+x2)/(2*w);cy=(y1+y2)/(2*h)
                        row=dict(zip(['frame0','time_s','track_id','confidence','x1','y1','x2','y2'],[frame,frame/fps,ID,score,*box]));post.append(row)
                        axis,perp=(cx,cy) if camera['axis']=='x' else (cy,cx)
                        if ID is not None and camera['perpendicular_ROI'][0]<perp<camera['perpendicular_ROI'][1]:
                            positions[ID]=axis;item={**row,'axis_position':axis};tracked.append(item);held.append(item)
                    for t in tracker.tracked_stracks:
                        if t.is_activated:continue
                        x1,y1,x2,y2=np.asarray(t.xyxy,np.float32).astype(float);cx=(x1+x2)/(2*w);cy=(y1+y2)/(2*h)
                        axis,perp=(cx,cy) if camera['axis']=='x' else (cy,cx)
                        if camera['perpendicular_ROI'][0]<perp<camera['perpendicular_ROI'][1]:tentative[int(t.track_id)]=axis
                    for output_events,target in [(counter.update(frame/fps,positions,tentative,active),events),(baseline.update(frame/fps,positions),plain)]:
                        for e in output_events:e['frame0']=frame;target.append(e)
                    trace.append({'frame0':frame,'time_s':frame/fps,'confirmed_positions':positions,'confirmed_IDs':sorted(active),'tentative_positions':tentative,
                                  'accepted_history':counter.last_acceptances});sample=frame
                view=image.copy();lo,hi=camera['perpendicular_ROI']
                if camera['axis']=='x':
                    cv2.rectangle(view,(0,round(h*lo)),(w-1,round(h*hi)),(0,177,255),2)
                    for value in [p['counter']['lower'],p['counter']['upper']]:cv2.line(view,(round(w*value),round(h*lo)),(round(w*value),round(h*hi)),(0,177,255),2)
                else:
                    cv2.rectangle(view,(round(w*lo),0),(round(w*hi),h-1),(0,177,255),2)
                    for value in [p['counter']['lower'],p['counter']['upper']]:cv2.line(view,(round(w*lo),round(h*value)),(round(w*hi),round(h*value)),(0,177,255),2)
                for row in held:
                    x1,y1,x2,y2=[round(row[k]) for k in ['x1','y1','x2','y2']];cv2.rectangle(view,(x1,y1),(x2,y2),(109,236,151),2)
                    cv2.putText(view,f"id {row['track_id']} {row['confidence']:.2f}",(x1,max(70,y1-6)),cv2.FONT_HERSHEY_SIMPLEX,.65,(109,236,151),2)
                a=sum(e['direction']=='A->B' for e in events);bcount=sum(e['direction']=='B->A' for e in events)
                cv2.rectangle(view,(0,0),(w,60),(17,24,39),-1)
                cv2.putText(view,f'{dest.name} | {clip["sequence"]}',(12,25),cv2.FONT_HERSHEY_SIMPLEX,.64,(240,240,240),2)
                cv2.putText(view,f'frame0 {frame}, sample {sample} | predicted A->B {a}, B->A {bcount}',(12,49),cv2.FONT_HERSHEY_SIMPLEX,.61,(240,240,240),1)
                cv2.rectangle(view,(0,h-28),(w,h),(17,24,39),-1)
                cv2.putText(view,'Prediction; complete-event reference pending. Track ID is not registered cow identity.',(12,h-8),cv2.FONT_HERSHEY_SIMPLEX,.53,(224,224,224),1)
                writer.stdin.write(view.tobytes());frame+=1
            cap.release();writer.stdin.close();assert writer.wait()==0
        except BaseException:
            cap.release()
            if writer.poll() is None:writer.terminate();writer.wait()
            raise
    assert frame==clip['frames'];fields=['frame0','time_s','track_id','confidence','x1','y1','x2','y2']
    csvsave(dest/'raw_detector_boxes.csv',raw,['frame0','time_s','confidence','x1','y1','x2','y2']);csvsave(dest/'post_tracker_boxes.csv',post,fields)
    csvsave(dest/'tracks.csv',tracked,fields+['axis_position']);save(dest/'observations.json',trace);save(dest/'handoff_events.json',events);save(dest/'confirmed_only_events.json',plain)
    result={'sequence':clip['sequence'],'model':dest.name,'frames':frame,'samples':len(trace),'stride':stride,'fps':fps,
            'raw_detector_rows':len(raw),'tracked_ROI_rows':len(tracked),'ROI_IDs':len({r['track_id'] for r in tracked}),
            'predicted_A_to_B':sum(e['direction']=='A->B' for e in events),'predicted_B_to_A':sum(e['direction']=='B->A' for e in events),
            'confirmed_only_predicted_events':len(plain),'handoff_predicted_events':len(events),
            'movie_sha256':sha(movie),'protocol_sha256':sha(ROOT/'protocol/inference_v1.json'),'full_event_GT_available':False,
            'server_detector_call_seconds':times,'timings_are_not_PYNQ_measurements':True,'FPGA_execution_verified':False,'whole_goal_complete':False}
    save(dest/'summary.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['server_detector_call_seconds']}),flush=True);return result

def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';torch.set_num_threads(4);cv2.setNumThreads(2)
    p=json.loads((ROOT/'protocol/inference_v1.json').read_text());assert ultralytics.__version__==p['ultralytics_version'] and torch.cuda.is_available()
    for name,digest in p['input_module_sha256'].items():assert sha(ROOT/'input'/name)==digest
    admission=ROOT/'results/admission/summary.json';assert sha(admission)==p['admission_summary_sha256']
    clips=json.loads(admission.read_text())['videos'];out=ROOT/'results/inference';out.mkdir(exist_ok=False);rows=[]
    for spec in p['models']:
        assert sha(Path(spec['checkpoint_path']))==spec['checkpoint_sha256'];model=YOLO(spec['checkpoint_path'])
        for clip in clips:rows.append(run(model,p,clip,out/clip['sequence']/spec['name']))
        del model;torch.cuda.empty_cache()
    summary={'status':'TWO_FROZEN_MODELS_ON_FOUR_OVERHEAD_SESSIONS_COMPLETE','job_id':os.environ['SLURM_JOB_ID'],
             'protocol_sha256':sha(ROOT/'protocol/inference_v1.json'),'conditions':rows,'conditions_count':len(rows),
             'new_model_forwards':sum(r['samples'] for r in rows),'training_updates':0,'per_event_GT_available':False,
             'current_confirmed_12_clip_changed':False,'FPGA_execution_verified':False,'whole_goal_complete':False}
    assert len(rows)==8;save(out/'summary.json',summary)
    import tarfile
    archive=ROOT/'inference_delivery.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        for folder in [ROOT/'protocol',ROOT/'input',out]:
            for f in folder.rglob('*'):
                if f.is_file() and f.suffix!='.avi' and 'prefix' not in f.name:tar.add(f,arcname=f.relative_to(ROOT))
    print(json.dumps({'status':summary['status'],'conditions':len(rows),'new_model_forwards':summary['new_model_forwards'],
                      'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive)}),flush=True)

if __name__=='__main__':main()
