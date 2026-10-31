"""Same source history and frozen settings; save only user-selected source clip."""
from pathlib import Path
import csv,hashlib,json,os,sys,time
import cv2,torch,numpy as np
from ultralytics import YOLO

PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT=PROJECT/'composition_control'
sys.path.insert(0,str(PROJECT/'phase2/tools'))
from zone_counter import ZoneCounter
from event_metrics import evaluate_events


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()


def save(path,value):Path(path).write_text(json.dumps(value,indent=2),encoding='utf-8')


def csv_write(path,rows,keys):
    with Path(path).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(rows)


def main():
    torch.set_num_threads(2);cv2.setNumThreads(1)
    assert torch.cuda.is_available()
    p=json.loads((ROOT/'protocol/composition_v1.json').read_text())
    freeze_path=ROOT/'results/all_models_frozen.json'
    freeze=json.loads(freeze_path.read_text());assert not freeze['source_or_Toros_inference_enabled_before_this_file']
    freeze_hash=sha(freeze_path)
    OUT=ROOT/'results/inference';OUT.mkdir(parents=True,exist_ok=False)
    conditions=[{'name':r['condition']['name'],
                 'title':f"{r['condition']['arm']}10 seed{r['condition']['seed']}",
                 'checkpoint':r['checkpoint'],'checkpoint_sha256':r['checkpoint_sha256'],
                 'seed':r['condition']['seed'],'arm':r['condition']['arm']} for r in freeze['conditions']]
    assert len(conditions)==6
    for condition in conditions:assert sha(condition['checkpoint'])==condition['checkpoint_sha256']
    source=PROJECT/'data/multicam_samples/camera1/2023-08-14T12-54-48.mp4'
    assert sha(source)=='5d1d8c197abbebfd98d11b7900fe2655013acc43cf5e01bebc7c72a3bcde95a1'
    toros=PROJECT/'phase2/data/mendeley_counting/extracted/Ground Truth/Toros.mp4'
    reference=json.loads((PROJECT/'phase2/results/author_gt_audit/summary.json').read_text())['events']
    assert len(reference)==6
    save(OUT/'toros_reference_events.json',reference)
    results=[];first,last=8912,10873
    for condition in conditions:
        dest=OUT/condition['name'];dest.mkdir()
        source_rows=[];external=None
        for scene,video in [('source',source),('Toros',toros)]:
            torch.manual_seed(26)
            model=YOLO(condition['checkpoint']);cls=next(k for k,v in model.names.items() if v=='cow')
            cap=cv2.VideoCapture(str(video));fps=cap.get(5);width=int(cap.get(3));height=int(cap.get(4));total=int(cap.get(7))
            if scene=='source':assert (fps,width,height)==(25.,2560,1440)
            else:assert (fps,total,width,height)==(30.,479,1920,1080)
            counter=ZoneCounter();tracks=[];warmup_tracks=[];events=[];detections=[];frames=[];held=[];last_sample=None
            writer=(cv2.VideoWriter(str(dest/'source_transfer.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),25.,(1280,720))
                    if scene=='source' else None)
            assert writer is None or writer.isOpened()
            start=time.perf_counter();processed=sampled=rendered=0
            extent=last+1 if scene=='source' else total
            for frame_index in range(extent):
                ok,frame=cap.read();assert ok,(scene,frame_index)
                processed+=1
                infer_now=frame_index%5==0 if scene=='source' else True
                if infer_now:
                    result=model.track(frame,persist=True,tracker='bytetrack.yaml',classes=[cls],imgsz=320,conf=.2,iou=.5,device=0,verbose=False)[0]
                    positions={};held=[];last_sample=frame_index
                    if result.boxes is not None:
                        boxes=result.boxes.xyxy.cpu().tolist();confidence=result.boxes.conf.cpu().tolist()
                        ids=result.boxes.id.int().cpu().tolist() if result.boxes.id is not None else [None]*len(boxes)
                        for box,conf,tid in zip(boxes,confidence,ids):
                            x1,y1,x2,y2=box;cx=(x1+x2)/2/width;cy=(y1+y2)/2/height
                            if scene=='Toros':detections.append({'frame':frame_index,'time_s':frame_index/fps,'track_id':tid,'confidence':conf,'x1':x1,'y1':y1,'x2':x2,'y2':y2})
                            valid=tid is not None and (.34<cx<.75 if scene=='source' else .1<cy<.95)
                            if not valid:continue
                            positions[tid]=cy if scene=='source' else cx
                            row={'source_frame':frame_index,'time_s':frame_index/fps,'track_id':tid,'confidence':conf,
                                 'x1':x1,'y1':y1,'x2':x2,'y2':y2,'axis_position':positions[tid]}
                            held.append(row)
                            if scene=='Toros' or frame_index>=first:tracks.append(row)
                            else:warmup_tracks.append(row)
                    for event in counter.update(frame_index/fps,positions):
                        event['source_frame']=frame_index
                        if scene=='Toros' or frame_index>=first:events.append(event)
                    if scene=='source' and frame_index>=first:frames.append({'source_frame':frame_index,'time_s':frame_index/fps,'tracked_ids':list(positions)})
                    sampled+=1
                if scene=='source' and frame_index>=first:
                    view=cv2.resize(frame,(1280,720),interpolation=cv2.INTER_AREA)
                    for x in [.34,.75]:cv2.line(view,(round(x*1280),0),(round(x*1280),719),(0,177,255),2)
                    for y in [.4,.6]:cv2.line(view,(round(.34*1280),round(y*720)),(round(.75*1280),round(y*720)),(0,177,255),2)
                    for row in held:
                        x1,y1,x2,y2=[round(row[k]/2) for k in ['x1','y1','x2','y2']]
                        cv2.rectangle(view,(x1,y1),(x2,y2),(112,237,149),2)
                        cv2.putText(view,f'track {row["track_id"]} {row["confidence"]:.2f}',(x1,max(70,y1-8)),cv2.FONT_HERSHEY_SIMPLEX,.65,(112,237,149),2)
                    down=sum(e['direction']=='A->B' for e in events);up=len(events)-down
                    cv2.rectangle(view,(0,0),(1280,57),(18,24,28),-1)
                    cv2.putText(view,condition['title'],(20,27),cv2.FONT_HERSHEY_SIMPLEX,.75,(240,242,240),2)
                    cv2.putText(view,f'Source f{frame_index} ({frame_index/25:.2f}s) | sample {last_sample} | down {down} up {up}',(20,49),cv2.FONT_HERSHEY_SIMPLEX,.57,(212,225,222),1)
                    cv2.rectangle(view,(0,688),(1280,720),(18,24,28),-1)
                    cv2.putText(view,'5 Hz actual inference, boxes held to next sample. Track IDs are not cow identities.',(20,709),cv2.FONT_HERSHEY_SIMPLEX,.57,(212,225,222),1)
                    writer.write(view);rendered+=1
                    if frame_index in [8912,9420,10873]:assert cv2.imwrite(str(dest/f'source_f{frame_index}.jpg'),view)
            cap.release()
            if writer:writer.release();assert rendered==1962 and sampled==2175 and processed==10874
            else:assert processed==sampled==479
            save(dest/f'{scene}_events.json',events)
            csv_write(dest/f'{scene}_tracks.csv',tracks,['source_frame','time_s','track_id','confidence','x1','y1','x2','y2','axis_position'])
            if scene=='source':csv_write(dest/'source_warmup_tracks.csv',warmup_tracks,['source_frame','time_s','track_id','confidence','x1','y1','x2','y2','axis_position'])
            save(dest/f'{scene}_sample_frames.json',frames)
            if scene=='Toros':
                csv_write(dest/'Toros_posttracker_boxes.csv',detections,['frame','time_s','track_id','confidence','x1','y1','x2','y2'])
                external=evaluate_events(reference,events,2.)
            record={'scene':scene,'source_sha256':sha(video),'processed_frames':processed,'sampled_inference_frames':sampled,
                    'rendered_frames':rendered,'A_to_B':sum(e['direction']=='A->B' for e in events),'B_to_A':sum(e['direction']=='B->A' for e in events),
                    'events':len(events),'elapsed_s_host_replay':time.perf_counter()-start,'counter_initialised_at_source_frame':0,
                    'source_output_frame_range':[first,last] if scene=='source' else [0,478],
                    'scope':'Previously observed development video; no new independent accuracy claim' if scene=='source' else 'Previously used6-event diagnostic; not fresh generalisation'}
            save(dest/f'{scene}_summary.json',record)
            source_rows.append(record)
            print(json.dumps({'model':condition['name'],**record}),flush=True)
            del model;torch.cuda.empty_cache()
        row={**condition,'scenes':source_rows,'Toros_event_metrics':external}
        save(dest/'summary.json',row);results.append(row)
    assert sha(freeze_path)==freeze_hash
    summary={'status':'SIX_COMPOSITION_MODELS_SOURCE_AND_KNOWN_DIAGNOSTIC_COMPLETE','job_id':os.environ['SLURM_JOB_ID'],
             'conditions':results,'training_freeze_sha256':freeze_hash,'protocol_sha256':sha(ROOT/'protocol/composition_v1.json'),
             'display_all_paired_conditions':True,'source_count_accuracy':None,'source_identity_accuracy':None,
             'scope':p['scope'],'device':torch.cuda.get_device_name(0)}
    save(OUT/'summary.json',summary)


if __name__=='__main__':main()
