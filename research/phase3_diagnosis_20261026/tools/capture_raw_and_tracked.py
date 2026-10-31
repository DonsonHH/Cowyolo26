"""Capture the detector/tracker seam without changing the frozen inference path."""
from pathlib import Path
import csv,hashlib,json,os,time,cv2,torch
import sys

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026')
PH=ROOT/'phase3_diagnosis';OLD=ROOT/'phase2'
os.environ['YOLO_CONFIG_DIR']=str(PH/'cache/ultralytics')
os.environ['YOLO_AUTOINSTALL']='false'
from ultralytics import YOLO
sys.path.insert(0,str(OLD/'tools'))
from zone_counter import ZoneCounter
PROTOCOL=json.loads((OLD/'annotations/evaluation_protocol_v1.json').read_text())
SOURCE=OLD/'data/mendeley_counting/extracted/Ground Truth/Toros.mp4'
DIAG=json.loads((PH/'annotations/diagnosis_protocol_v1.json').read_text())
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==DIAG['source_sha256']
assert torch.cuda.is_available()
weights={'generic':ROOT/'models/yolo26n.pt','pilot':ROOT/'results/detection_pilot/five_epoch_dev/weights/best.pt'}
previous=json.loads((OLD/'results/external_counting/all_summaries.json').read_text())
summary=[]
for name,checkpoint in weights.items():
    digest=hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    assert digest==PROTOCOL['weights'][name]['sha256']
    dest=PH/'results/capture'/name
    dest.mkdir(parents=True,exist_ok=False)
    model=YOLO(str(checkpoint));cls=next(k for k,v in model.names.items() if v=='cow')
    raw=[];post=[];tracks=[];events=[];counter=ZoneCounter();frame=0;callback_frames=[]
    def capture_before_tracker(predictor):
        assert len(predictor.results)==1
        result=predictor.results[0]
        boxes=result.boxes
        assert boxes.id is None,'Raw hook executed after tracker or stale tracking boxes'
        callback_frames.append(frame)
        for box,confidence in zip(boxes.xyxy.detach().cpu().tolist(),boxes.conf.detach().cpu().tolist()):
            raw.append({'frame':frame,'time_s':frame/30,'confidence':confidence,
                        **dict(zip(['x1','y1','x2','y2'],box))})
    model.add_callback('on_predict_postprocess_end',capture_before_tracker)
    cap=cv2.VideoCapture(str(SOURCE));fps=cap.get(5);n=int(cap.get(7));w=cap.get(3);h=cap.get(4)
    assert (fps,n,int(w),int(h))==(30.,479,1920,1080)
    t0=time.perf_counter()
    while True:
        ok,image=cap.read()
        if not ok:break
        result=model.track(image,persist=True,tracker='bytetrack.yaml',classes=[cls],
                           imgsz=320,conf=.2,iou=.5,device=0,verbose=False)[0]
        boxes=result.boxes;positions={}
        if boxes is not None:
            ids=boxes.id.int().cpu().tolist() if boxes.id is not None else [None]*len(boxes)
            for box,confidence,tid in zip(boxes.xyxy.cpu().tolist(),boxes.conf.cpu().tolist(),ids):
                x1,y1,x2,y2=box;cx=(x1+x2)/2/w;cy=(y1+y2)/2/h
                post.append({'frame':frame,'time_s':frame/fps,'track_id':tid,'confidence':confidence,
                             **dict(zip(['x1','y1','x2','y2'],box))})
                if tid is not None and .1<cy<.95:
                    positions[tid]=cx
                    tracks.append({'frame':frame,'time_s':frame/fps,'track_id':tid,'axis_position':cx,'cy_norm':cy})
        for event in counter.update(frame/fps,positions):event['frame']=frame;events.append(event)
        frame+=1
    cap.release()
    assert frame==n and callback_frames==list(range(n))
    expected=next(r for r in previous if r['model']==name and r['video']=='Toros')
    assert events==expected['events'],'Instrumented path changed frozen baseline events'
    callbacks=[getattr(c,'func',c) for c in model.predictor.callbacks['on_predict_postprocess_end']]
    order=[{'name':getattr(c,'__name__',str(type(c))), 'module':getattr(c,'__module__','')} for c in callbacks]
    tracker_index=next(i for i,c in enumerate(order) if c['module']=='ultralytics.trackers.track' and c['name']=='on_predict_postprocess_end')
    assert callbacks.index(capture_before_tracker)<tracker_index
    for filename,rows,keys in [
        ('raw_detector_boxes.csv',raw,['frame','time_s','confidence','x1','y1','x2','y2']),
        ('post_tracker_boxes.csv',post,['frame','time_s','track_id','confidence','x1','y1','x2','y2']),
        ('tracks.csv',tracks,['frame','time_s','track_id','axis_position','cy_norm']),
        ('events.csv',events,['time_s','track_id','direction','frame'])]:
        with (dest/filename).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(rows)
    row={'model':name,'job_id':os.environ['SLURM_JOB_ID'],'checkpoint_sha256':digest,
         'frames':frame,'raw_boxes':len(raw),'post_tracker_boxes':len(post),'events':events,
         'callback_order':order,'frozen_baseline_event_equality':True,
         'elapsed_s':time.perf_counter()-t0,'cuda_device':torch.cuda.get_device_name(0)}
    (dest/'summary.json').write_text(json.dumps(row,indent=2));summary.append(row)
    print(json.dumps(row),flush=True)
(PH/'results/capture/summary.json').write_text(json.dumps(summary,indent=2))
