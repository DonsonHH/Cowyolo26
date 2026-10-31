"""Three fixed checkpoints, raw-before-tracker seam and same actual event gate."""
from pathlib import Path
import csv,functools,hashlib,json,os,sys,time
import cv2,torch
PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT=PROJECT/'event_diagnosis'
os.environ['YOLO_CONFIG_DIR']=str(ROOT/'cache/ultralytics');os.environ['YOLO_AUTOINSTALL']='false'
from ultralytics import YOLO
sys.path.insert(0,str(PROJECT/'phase2/tools'))
from zone_counter import ZoneCounter


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2))


def main():
    torch.set_num_threads(2);cv2.setNumThreads(1);assert torch.cuda.is_available()
    p=json.loads((ROOT/'protocol/event_diagnosis_v1.json').read_text())
    source=PROJECT/'phase2/data/mendeley_counting/extracted/Ground Truth/Toros.mp4'
    assert sha(source)==p['toros_sha256']
    OUT=ROOT/'results/capture';OUT.mkdir(parents=True,exist_ok=False);summary=[]
    for condition in p['models']:
        name=condition['name'];checkpoint=Path(condition['checkpoint']);assert sha(checkpoint)==condition['checkpoint_sha256']
        dest=OUT/name;dest.mkdir();model=YOLO(str(checkpoint));assert model.names=={0:'cow'}
        raw=[];post=[];tracks=[];events=[];counter=ZoneCounter();frame_index=0;hook_frames=[]
        def before_tracker(predictor):
            assert len(predictor.results)==1
            boxes=predictor.results[0].boxes;assert boxes.id is None
            hook_frames.append(frame_index)
            for box,confidence in zip(boxes.xyxy.cpu().tolist(),boxes.conf.cpu().tolist()):
                raw.append({'frame':frame_index,'time_s':frame_index/30,'confidence':confidence,**dict(zip(['x1','y1','x2','y2'],box))})
        model.add_callback('on_predict_postprocess_end',before_tracker)
        cap=cv2.VideoCapture(str(source));assert (cap.get(5),int(cap.get(7)))==(30.,479)
        start=time.perf_counter()
        while True:
            ok,image=cap.read()
            if not ok:break
            result=model.track(image,persist=True,tracker='bytetrack.yaml',classes=[0],imgsz=320,conf=.2,iou=.5,device=0,verbose=False)[0]
            boxes=result.boxes;positions={}
            if boxes is not None:
                ids=boxes.id.int().cpu().tolist() if boxes.id is not None else [None]*len(boxes)
                for box,conf,tid in zip(boxes.xyxy.cpu().tolist(),boxes.conf.cpu().tolist(),ids):
                    x1,y1,x2,y2=box;cx=(x1+x2)/3840;cy=(y1+y2)/2160
                    post.append({'frame':frame_index,'time_s':frame_index/30,'track_id':tid,'confidence':conf,**dict(zip(['x1','y1','x2','y2'],box))})
                    if tid is not None and .1<cy<.95:
                        positions[tid]=cx;tracks.append({'frame':frame_index,'time_s':frame_index/30,'track_id':tid,'axis_position':cx,'cy_norm':cy})
            for event in counter.update(frame_index/30,positions):events.append({**event,'frame':frame_index})
            frame_index+=1
        cap.release();assert frame_index==479 and hook_frames==list(range(479))
        expected=json.loads((PROJECT/f'detector_training/results/inference/{name}/Toros_events.json').read_text())
        canonical=lambda e:{'time_s':e['time_s'],'track_id':e['track_id'],'direction':e['direction'],'frame':e.get('frame',e.get('source_frame'))}
        assert events==[canonical(e) for e in expected],'Seam changed actual frozen events'
        callbacks=[getattr(c,'func',c) for c in model.predictor.callbacks['on_predict_postprocess_end']]
        order=[{'name':getattr(c,'__name__',''),'module':getattr(c,'__module__','')} for c in callbacks]
        tracker=next(i for i,r in enumerate(order) if r['module']=='ultralytics.trackers.track' and r['name']=='on_predict_postprocess_end')
        assert callbacks.index(before_tracker)<tracker
        for filename,rows,keys in [('raw_detector_boxes.csv',raw,['frame','time_s','confidence','x1','y1','x2','y2']),
             ('post_tracker_boxes.csv',post,['frame','time_s','track_id','confidence','x1','y1','x2','y2']),
             ('tracks.csv',tracks,['frame','time_s','track_id','axis_position','cy_norm']),('events.csv',events,['time_s','track_id','direction','frame'])]:
            with (dest/filename).open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
        row={'model':name,'job_id':os.environ['SLURM_JOB_ID'],'checkpoint_sha256':sha(checkpoint),'frames':frame_index,
             'raw_boxes':len(raw),'post_tracker_boxes':len(post),'events':events,'callback_order':order,
             'frozen_baseline_event_equality':True,'elapsed_s':time.perf_counter()-start,'cuda_device':torch.cuda.get_device_name(0)}
        save(dest/'summary.json',row);summary.append(row);print(json.dumps(row),flush=True)
    save(OUT/'summary.json',summary)


if __name__=='__main__':main()
