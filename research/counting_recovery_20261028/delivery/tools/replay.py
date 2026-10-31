from pathlib import Path
from collections import defaultdict
import csv,json,os,sys,time,hashlib,functools
import cv2,numpy as np,torch
from ultralytics import YOLO
from native_restore import callback,controls
PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026');ROOT=PROJECT/'counting_recovery_20261028'
sys.path.insert(0,str(PROJECT/'phase2/tools'))
from zone_counter import ZoneCounter
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2),encoding='utf-8')
def writecsv(path,rows,fields):
    with Path(path).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def normalize(rows):
    return [{k:None if v in [None,''] else int(v) if k in ['source_frame','track_id'] else float(v) for k,v in r.items()} for r in rows]

def run(p,arm,weight,out):
    name=arm['name']+f'_seed{weight["seed"]}';dest=out/name;dest.mkdir(exist_ok=False)
    assert sha(weight['checkpoint'])==weight['sha256']
    torch.manual_seed(26);model=YOLO(weight['checkpoint']);cow=next(k for k,v in model.names.items() if v=='cow')
    counter=ZoneCounter(stable_samples=arm['stable_samples']);dense=ZoneCounter() if arm['stride']==1 else None
    raw,seams,tracks,history,events,other_events,allboxes,frames=[],[],[],[],[],[],[],[]
    holder={'image':None,'frame':0,'crop':arm['crop_x']};restore=callback(holder,raw,seams)
    model.add_callback('on_predict_postprocess_end',restore)
    cap=cv2.VideoCapture(p['source_video']);assert (cap.get(5),int(cap.get(3)),int(cap.get(4)))==(25.,2560,1440)
    writer=cv2.VideoWriter(str(dest/'transfer.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),25.,(1280,720));assert writer.isOpened()
    started=time.perf_counter();held=[];timings=[];scoped_raw_frames=set();scoped_track_frames=set()
    first,last=p['source_scope_inclusive'];left,right=arm['crop_x'];sample=None
    for frame in range(last+1):
        ok,image=cap.read();assert ok,(name,frame)
        if frame%arm['stride']==0:
            holder.update(image=image,frame=frame);model_input=np.rot90(image[:,left:right],k=-1).copy()
            tick=time.perf_counter();result=model.track(model_input,persist=True,tracker=p['tracker'],classes=[cow],
                imgsz=arm['imgsz'],conf=arm['confidence'],iou=.5,device=0,verbose=False)[0]
            timings.append(time.perf_counter()-tick);sample=frame
            assert result.orig_shape==(1440,2560)
            # callbackexecuted in nativecoordinates beforeByteTrack.
            functions=[getattr(c,'func',c) for c in model.predictor.callbacks['on_predict_postprocess_end']]
            if len(seams)==1:
                ti=next(i for i,c in enumerate(functions) if c.__module__=='ultralytics.trackers.track')
                assert functions.index(restore)<ti
            recent=raw[-seams[-1]['raw_boxes']:] if seams[-1]['raw_boxes'] else []
            if frame>=first and any(.34<(r['x1']+r['x2'])/5120<.75 for r in recent):scoped_raw_frames.add(frame)
            held=[];positions={}
            boxes=result.boxes
            if boxes is not None:
                ids=boxes.id.int().cpu().tolist() if boxes.id is not None else [None]*len(boxes)
                for box,conf,tid in zip(boxes.xyxy.cpu().tolist(),boxes.conf.cpu().tolist(),ids):
                    x1,y1,x2,y2=box
                    allboxes.append({'frame':frame,'track_id':tid,'confidence':conf,'x1':x1,'y1':y1,'x2':x2,'y2':y2})
                    if tid is None or not .34<(x1+x2)/5120<.75:continue
                    row={'source_frame':frame,'time_s':frame/25,'track_id':tid,'confidence':conf,
                         'x1':x1,'y1':y1,'x2':x2,'y2':y2,'axis_position':(y1+y2)/2880}
                    positions[tid]=row['axis_position'];held.append(row)
                    if frame>=first:tracks.append(row);scoped_track_frames.add(frame)
                    else:history.append(row)
            for event in counter.update(frame/25,positions):
                event['source_frame']=frame
                if frame>=first:events.append(event)
            if dense:
                for event in dense.update(frame/25,positions):
                    event['source_frame']=frame
                    if frame>=first:other_events.append(event)
            frames.append({'frame':frame,'track_ids':list(positions)})
        if frame<first:continue
        view=cv2.resize(image,(1280,720),interpolation=cv2.INTER_AREA)
        for x in [.34,.75]:cv2.line(view,(round(1280*x),0),(round(1280*x),719),(0,177,255),2)
        for y in [.4,.6]:cv2.line(view,(round(.34*1280),round(y*720)),(round(.75*1280),round(y*720)),(0,177,255),2)
        for row in held:
            x1,y1,x2,y2=[round(row[k]/2) for k in ['x1','y1','x2','y2']]
            cv2.rectangle(view,(x1,y1),(x2,y2),(112,237,149),2)
            cv2.putText(view,f'id {row["track_id"]} {row["confidence"]:.2f}',(x1,max(62,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,.6,(112,237,149),2)
        down=sum(e['direction']=='A->B' for e in events);up=len(events)-down
        cv2.rectangle(view,(0,0),(1280,56),(18,24,28),-1)
        cv2.putText(view,name,(16,25),cv2.FONT_HERSHEY_SIMPLEX,.68,(240,242,240),2)
        cv2.putText(view,f'Source {frame} sample {sample} | predicted down {down} up {up}',(16,48),cv2.FONT_HERSHEY_SIMPLEX,.59,(220,228,225),1)
        cv2.rectangle(view,(0,690),(1280,720),(18,24,28),-1)
        cv2.putText(view,'Development predictions. Native coordinates; track ID is not registered cow identity.',(16,710),cv2.FONT_HERSHEY_SIMPLEX,.57,(220,228,225),1)
        writer.write(view)
        if frame in [8912,9345,9420,9550,9700,10873]:assert cv2.imwrite(str(dest/f'f{frame}.jpg'),view)
    writer.release();cap.release()
    save(dest/'source_events.json',events);save(dest/'dense_3sample_diagnostic_events.json',other_events)
    fields=['source_frame','time_s','track_id','confidence','x1','y1','x2','y2','axis_position']
    writecsv(dest/'source_tracks.csv',tracks,fields);writecsv(dest/'source_warmup_tracks.csv',history,fields)
    writecsv(dest/'pretracker_boxes.csv',raw,['frame','confidence','u1','v1','u2','v2','x1','y1','x2','y2'])
    writecsv(dest/'all_posttracker_boxes.csv',allboxes,['frame','track_id','confidence','x1','y1','x2','y2'])
    save(dest/'seam_checks.json',seams)
    if arm['name']=='baseline_full320_5hz':
        prior=ROOT/f'input/baseline_seed{weight["seed"]}'
        assert events==json.loads((prior/'source_events.json').read_text()),'Frozenbaselineeventdrift'
        for filename,rows in [('source_tracks.csv',tracks),('source_warmup_tracks.csv',history)]:
            assert normalize(rows)==normalize(list(csv.DictReader((prior/filename).open()))),'Frozenbaselinetrackdrift'
    record={'name':name,'arm':arm,'seed':weight['seed'],'checkpoint_sha256':weight['sha256'],
        'sampled_frames_in_scope':sum(f%arm['stride']==0 for f in range(first,last+1)),
        'raw_ROI_frames':len(scoped_raw_frames),'tracked_ROI_frames':len(scoped_track_frames),
        'ROI_track_IDs':len({r['track_id'] for r in tracks}),
        'predicted_down':sum(e['direction']=='A->B' for e in events),'predicted_up':sum(e['direction']=='B->A' for e in events),
        'source_output_frames':1962,'history_start':0,'max_inverse_rounding_error':max(r['inverse_rounding_error'] for r in seams),
        'baseline_exact_regression':arm['name']=='baseline_full320_5hz','decode_replay_elapsed_s':time.perf_counter()-started,
        'host_call_median_ms':1000*float(np.median(timings)),'host_call_p95_ms':1000*float(np.quantile(timings,.95)),
        'dense3sample_diagnostic_events':len(other_events),'source_accuracy':None,'board_execution':False}
    save(dest/'summary.json',record);print(json.dumps(record),flush=True)
    del model;torch.cuda.empty_cache();return record

def main():
    assert os.environ.get('SLURM_JOB_ID') and torch.cuda.is_available()
    assert __import__('socket').gethostname()!='mu01'
    torch.set_num_threads(2);cv2.setNumThreads(1)
    p=json.loads((ROOT/'protocol/recovery_v1.json').read_text());assert __import__('ultralytics').__version__==p['library_ultralytics']
    assert sha(p['source_video'])==p['source_sha256'];geometry=controls()
    out=ROOT/'results/replay';out.mkdir(exist_ok=False)
    save(out/'frozen_run_config.json',{'protocol_sha256':sha(ROOT/'protocol/recovery_v1.json'),'geometry_controls':geometry,'protocol':p})
    pilot=next(r for r in p['weights'] if r['seed']==p['pilot_seed'])
    results=[run(p,arm,pilot,out) for arm in p['arms']]
    eligible=[r for r in results if r['arm']['stride']==5]
    selected=max(eligible,key=lambda r:(r['raw_ROI_frames'],-r['arm']['imgsz'],r['arm']['name']))
    save(out/'selection_before_other_seeds.json',{'rule':p['all_seed_verification'],'arm':selected['arm'],
         'raw_ROI_frames':selected['raw_ROI_frames'],'count_target_used':False})
    for weight in p['weights']:
        if weight['seed']==p['pilot_seed']:continue
        results.append(run(p,selected['arm'],weight,out))
    save(out/'summary.json',{'status':'SIX_FIXED_PILOT_ARMS_AND_THREE_SEED_SELECTED_ARM_COMPLETE',
        'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/recovery_v1.json'),
        'conditions':results,'selected_arm':selected['arm'],'all_conditions_reported':True,
        'independent_source_accuracy':None,'new_training_updates':0,'board_execution':False,'whole_goal_complete':False})

if __name__=='__main__':main()
