"""Paired video input rotation; boxes restored before native-coordinate tracking."""
from pathlib import Path
import csv,hashlib,json,os,sys,time
import cv2,torch,numpy as np
from ultralytics import YOLO
from rotation_seam import geometry_controls,make_restore_callback,callback_order

PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT=PROJECT/'orientation_video_20261027'
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
    p=json.loads((ROOT/'protocol/video_rotation_v1.json').read_text())
    for item in json.loads((ROOT/'input/staging_manifest.json').read_text()):
        assert sha(ROOT/item['path'])==item['sha256']
    for item in json.loads((ROOT/'input/counter_source_snapshot.json').read_text()):
        assert sha(Path(item['path']))==item['sha256']
    smoke_path=ROOT/'results/smoke.json'
    smoke=json.loads(smoke_path.read_text())
    assert smoke['status']=='SYNTHETIC_NONEMPTY_EMPTY_RESULTS_AND_REAL_BYTE_TRACK_SEAM_CONTROLS_PASS'
    assert smoke['protocol_sha256']==sha(ROOT/'protocol/video_rotation_v1.json')
    controls=geometry_controls()
    assert p['seeds']==[26,27,28] and p['epochs']==10
    assert p['source_replay']['first_frame_inclusive']==8912 and p['source_replay']['last_frame_inclusive']==10873
    assert p['source_replay']['confidence']==.2 and p['source_replay']['iou']==.5 and p['source_replay']['imgsz']==320
    assert os.environ.get('SLURM_JOB_ID') and __import__('socket').gethostname()!='mu01'
    assert __import__('ultralytics').__version__==p['library']['ultralytics']
    freeze_path=PROJECT/'cows2021_adaptation_20261027/results/training/all_checkpoints_frozen_before_video.json'
    freeze=json.loads(freeze_path.read_text())
    assert freeze['source_Toros_or_candidate_final_forward_before_freeze'] is False
    assert freeze['protocol_sha256']==p['prior_Cows_training_protocol_sha256']
    assert sha(freeze_path)==p['source_weights_freeze_sha256']
    assert freeze['all_seeds_retained'] is True
    training=json.loads((PROJECT/'cows2021_adaptation_20261027/results/training/summary.json').read_text())
    assert training['status']=='ALL_THREE_COWS2021_SEEDS_10_EPOCHS_COMPLETE_FROZEN_BEFORE_VIDEO'
    assert training['freeze_sha256']==sha(freeze_path)
    freeze_hash=sha(freeze_path)
    OUT=ROOT/'results/inference';OUT.mkdir(parents=True,exist_ok=False)
    conditions=[{'name':f"{orientation}_seed{r['seed']}",'title':f"Cows seed{r['seed']} input {orientation}",
                 'checkpoint':r['checkpoint'],'checkpoint_sha256':r['checkpoint_sha256'],
                 'seed':r['seed'],'orientation':orientation,'arm':'Cows2021_date_grouped'}
                 for r in freeze['conditions'] for orientation in p['orientations']]
    assert [c['seed'] for c in conditions]==[26,26,27,27,28,28] and len(conditions)==6
    save(OUT/'all_conditions_fixed_before_replay.json',{'protocol_sha256':sha(ROOT/'protocol/video_rotation_v1.json'),
         'prior_weight_freeze_sha256':sha(freeze_path),'geometry_controls':controls,
         'conditions':conditions,'created_unix':time.time(),'new_training_updates':0})
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
            raw=[];hook_frames=[];seam_checks=[];holder={'image':None,'frame_index':None}
            restore=make_restore_callback(condition['orientation'],holder,fps,raw,hook_frames,seam_checks)
            model.add_callback('on_predict_postprocess_end',restore)
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
                    holder.update(image=frame,frame_index=frame_index)
                    model_input=frame if condition['orientation']=='original' else np.rot90(frame,k=-1).copy()
                    result=model.track(model_input,persist=True,tracker='bytetrack.yaml',classes=[cls],imgsz=320,conf=.2,iou=.5,device=0,verbose=False)[0]
                    assert result.orig_shape==frame.shape[:2]
                    positions={};held=[];last_sample=frame_index
                    if result.boxes is not None:
                        boxes=result.boxes.xyxy.cpu().tolist();confidence=result.boxes.conf.cpu().tolist()
                        ids=result.boxes.id.int().cpu().tolist() if result.boxes.id is not None else [None]*len(boxes)
                        for box,conf,tid in zip(boxes,confidence,ids):
                            x1,y1,x2,y2=box;cx=(x1+x2)/2/width;cy=(y1+y2)/2/height
                            detections.append({'frame':frame_index,'time_s':frame_index/fps,'track_id':tid,'confidence':conf,'x1':x1,'y1':y1,'x2':x2,'y2':y2})
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
            order=callback_order(model,restore)
            assert hook_frames==list(range(0,extent,5) if scene=='source' else range(extent))
            save(dest/f'{scene}_seam_checks.json',{'callback_order':order,'checks':seam_checks,'detector_coordinate_restore_before_tracker':True})
            csv_write(dest/f'{scene}_pretracker_boxes.csv',raw,['frame','time_s','confidence','input_x1','input_y1','input_x2','input_y2','x1','y1','x2','y2'])
            csv_write(dest/f'{scene}_all_posttracker_boxes.csv',detections,['frame','time_s','track_id','confidence','x1','y1','x2','y2'])
            if condition['orientation']=='original':
                baseline=ROOT/'input/baseline'/f"seed{condition['seed']}"
                assert events==json.loads((baseline/f'{scene}_events.json').read_text()),'Original event regression'
                prior_tracks=list(csv.DictReader((baseline/f'{scene}_tracks.csv').open()))
                def normalise_trace(rows):
                    return [{k:(None if v is None or v=='' else int(v) if k in ['source_frame','track_id'] else float(v)) for k,v in row.items()} for row in rows]
                assert normalise_trace(tracks)==normalise_trace(prior_tracks),'Original track regression'
                if scene=='source':
                    old=list(csv.DictReader((baseline/'source_warmup_tracks.csv').open()))
                    assert normalise_trace(warmup_tracks)==normalise_trace(old),'Original history regression'
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
                    'detector_input_orientation':condition['orientation'],
                    'tracker_and_counter_coordinate_system':'original native camera',
                    'detector_pretracker_boxes':len(raw),'posttracker_boxes_all_ROIs':len(detections),
                    'original_condition_prior_events_and_tracks_reproduced':True if condition['orientation']=='original' else None,
                    'scope':'Previously observed development video; no new independent accuracy claim' if scene=='source' else 'Previously used6-event diagnostic; not fresh generalisation'}
            save(dest/f'{scene}_summary.json',record)
            source_rows.append(record)
            print(json.dumps({'model':condition['name'],**record}),flush=True)
            del model;torch.cuda.empty_cache()
        row={**condition,'scenes':source_rows,'Toros_event_metrics':external}
        save(dest/'summary.json',row);results.append(row)
    assert sha(freeze_path)==freeze_hash
    summary={'status':'SIX_VIDEO_ROTATION_CONDITIONS_COMPLETE_ORIGINAL_TRACES_REPRODUCED','job_id':os.environ['SLURM_JOB_ID'],
             'conditions':results,'training_freeze_sha256':freeze_hash,'protocol_sha256':sha(ROOT/'protocol/video_rotation_v1.json'),
             'all_three_seeds_and_two_orientations_reported':True,'new_training_updates':0,'source_count_accuracy':None,'source_identity_accuracy':None,
             'scope':p['scope'],'device':torch.cuda.get_device_name(0)}
    save(OUT/'summary.json',summary)


if __name__=='__main__':main()
