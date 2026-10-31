"""Real decoded-video capture, bounded snapshots, GPU detection and CPU Re-ID."""
from pathlib import Path
import csv,hashlib,io,json,multiprocessing,os,queue,resource,sys,time
from collections import Counter
from snapshot_bank import Snapshot,SnapshotBank,clipped_box
from identity_worker import worker_main

PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026');ROOT=PROJECT/'video_chain'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def atomic_bytes(path,data):
    temporary=path.with_name(path.name+'.partial');temporary.write_bytes(data);temporary.replace(path)
def main():
    import cv2,numpy as np,torch
    from PIL import Image
    os.environ['YOLO_AUTOINSTALL']='false';os.environ['YOLO_CONFIG_DIR']=str(ROOT/'cache/ultralytics')
    (ROOT/'cache/ultralytics/Ultralytics').mkdir(parents=True,exist_ok=True)
    from ultralytics import YOLO
    sys.path.insert(0,str(PROJECT/'phase2/tools'));from zone_counter import ZoneCounter
    OUT=ROOT/'results/replay';OUT.mkdir(parents=True,exist_ok=False)
    for name in ['photos','quality','events']:(OUT/name).mkdir()
    protocol_path=ROOT/'protocol/video_chain_v1.json';p=json.loads(protocol_path.read_text())
    source=PROJECT/p['source_video'];assert sha(source)==p['source_video_sha256']
    weights=PROJECT/'results/detection_pilot/five_epoch_dev/weights/best.pt';assert sha(weights)==p['detector_weights_sha256']
    torch.set_num_threads(1);cv2.setNumThreads(1);torch.manual_seed(26)
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    assert torch.cuda.is_available()
    ctx=multiprocessing.get_context('spawn');tasks=ctx.Queue(maxsize=4);results=ctx.Queue(maxsize=16)
    child=ctx.Process(target=worker_main,args=(tasks,results,p,str(PROJECT)))
    child.start();ready=results.get(timeout=120)
    assert ready['kind']=='ready',ready
    assert ready['pid']!=os.getpid() and ready['device']=='cpu' and ready['conditions']==5
    (OUT/'worker_ready.json').write_text(json.dumps(ready,indent=2))
    model=YOLO(str(weights));cls=next(k for k,v in model.names.items() if v=='cow')
    cap=cv2.VideoCapture(str(source));fps=cap.get(5);w=int(cap.get(3));h=int(cap.get(4))
    assert (fps,w,h)==(25.,2560,1440)
    bank=SnapshotBank();counter=ZoneCounter();events={};pending=[];frames=[];tracks=[];messages=[]
    journal=(OUT/'events.jsonl').open('w',encoding='utf-8');front_start=time.monotonic_ns();bank_max=0
    def log(event_id,transition,**fields):
        journal.write(json.dumps({'event_id':event_id,'transition':transition,'wall_ns':time.monotonic_ns(),**fields})+'\n')
        journal.flush();os.fsync(journal.fileno())
    def record_result(message):
        messages.append(message)
        if message['kind']!='result':return
        identity=message['event_id'];row=events[identity]
        assert row['status']=='QUEUED','Result without exactly one pending task'
        message['main_received_wall_ns']=time.monotonic_ns();row['worker_result']=message
        if message['status']=='COMPLETED':
            assert len(message['conditions'])==5
            row['status']='CANDIDATES_READY_UNVERIFIED' if any(c['passes_frozen_threshold'] for c in message['conditions']) else 'ALL_CONDITIONS_REJECTED'
        else:row['status']='UNRESOLVED_'+message['status']
        (OUT/'events'/f'{identity}.json').write_text(json.dumps(row,indent=2));log(identity,row['status'],worker_status=message['status'])
    def poll():
        while True:
            try:message=results.get_nowait()
            except queue.Empty:break
            record_result(message)
    def capture(e,source_frame,observed_ns):
        identity=f'event-{len(events)+1:03d}-f{source_frame}-t{e["track_id"]}'
        choices=bank.take(e['track_id'],e['time_s'])
        row={'event_id':identity,'source_frame':source_frame,'source_time_s':e['time_s'],'track_id':e['track_id'],'direction':e['direction'],
             'observed_wall_ns':observed_ns,'rf_status':'RF_INPUT_NOT_CONNECTED_MOCK_MISS_BRANCH','rf_deadline_source_s':e['time_s']+.5,
             'status':'PENDING_RF_WINDOW','candidate_quality_records':[],'verified_identity':False}
        for i,(snapshot,jpeg) in enumerate(choices):
            quality_path=OUT/'quality'/f'{identity}-choice{i+1}-f{snapshot.frame}.png';atomic_bytes(quality_path,snapshot.quality_png)
            row['candidate_quality_records'].append({'source_frame':snapshot.frame,'source_time_s':snapshot.source_time,'decoded_wall_ns':snapshot.decoded_wall_ns,
                    'box':list(snapshot.box),'quality':snapshot.quality,'detector_confidence':snapshot.confidence,
                    'quality_png_path':str(quality_path.relative_to(OUT)),'quality_png_sha256':sha(quality_path)})
        events[identity]=row;log(identity,'EVENT_OBSERVED',source_frame=source_frame,direction=e['direction'])
        if not choices:
            row['status']='UNRESOLVED_NO_SNAPSHOT';(OUT/'events'/f'{identity}.json').write_text(json.dumps(row,indent=2));log(identity,row['status']);return
        snapshot,jpeg=choices[0]
        photo_path=OUT/'photos'/f'{identity}-native.jpg';atomic_bytes(photo_path,jpeg)
        with Image.open(io.BytesIO(jpeg)) as image:
            image=image.convert('RGB');assert image.size==(w,h)
            crop=image.crop(snapshot.box)
            oriented=crop.transpose(Image.Transpose.ROTATE_90 if e['direction']=='A->B' else Image.Transpose.ROTATE_270)
        crop_path=OUT/'photos'/f'{identity}-crop.png';oriented_path=OUT/'photos'/f'{identity}-oriented.png'
        for path,image in [(crop_path,crop),(oriented_path,oriented)]:
            stream=io.BytesIO();image.save(stream,format='PNG');atomic_bytes(path,stream.getvalue())
        row['selected_snapshot']={**row['candidate_quality_records'][0],'native_photo_path':str(photo_path.relative_to(OUT)),
             'native_photo_sha256':sha(photo_path),'native_photo_size':[w,h],'crop_path':str(crop_path.relative_to(OUT)),
             'crop_sha256':sha(crop_path),'crop_size':list(crop.size),'rotation_ccw_degrees':90 if e['direction']=='A->B' else 270,
             'oriented_crop_path':str(oriented_path.relative_to(OUT)),'oriented_crop_sha256':sha(oriented_path),'oriented_crop_size':list(oriented.size)}
        row['capture_saved_wall_ns']=time.monotonic_ns();pending.append(identity)
        (OUT/'events'/f'{identity}.json').write_text(json.dumps(row,indent=2));log(identity,'SNAPSHOT_SAVED',selected_source_frame=snapshot.frame)
    def advance_mock_rf(source_time):
        for identity in list(pending):
            row=events[identity]
            if source_time<row['rf_deadline_source_s']:continue
            pending.remove(identity);row['rf_observation_horizon_source_s']=source_time
            now=time.monotonic_ns();row['enqueue_wall_ns']=now;row['deadline_wall_ns']=now+30_000_000_000
            selected=row['selected_snapshot']
            job={'event_id':identity,'oriented_crop_path':str(OUT/selected['oriented_crop_path']),
                 'oriented_crop_sha256':selected['oriented_crop_sha256'],'deadline_wall_ns':row['deadline_wall_ns']}
            if not child.is_alive():row['status']='UNRESOLVED_WORKER_NOT_ALIVE'
            else:
                try:tasks.put_nowait(job);row['status']='QUEUED'
                except queue.Full:row['status']='UNRESOLVED_QUEUE_CAPACITY'
            (OUT/'events'/f'{identity}.json').write_text(json.dumps(row,indent=2));log(identity,row['status'],mock_rf_horizon_source_s=source_time)
    decoded=sampled=0
    try:
        for idx in range(14008):
            loop_start=time.monotonic_ns();ok,frame=cap.read()
            if not ok:raise RuntimeError(f'Decode stopped early at source frame{idx}')
            decoded+=1
            if idx%5:continue
            decoded_ns=time.monotonic_ns();source_time=idx/fps;bank.advance(source_time);poll()
            torch.cuda.synchronize();det_before=time.monotonic_ns()
            result=model.track(frame,persist=True,tracker='bytetrack.yaml',classes=[cls],imgsz=320,conf=.2,iou=.5,device=0,verbose=False)[0]
            torch.cuda.synchronize();det_after=time.monotonic_ns();positions={};encoded_now=None;encode_ns=0
            def jpeg():
                nonlocal encoded_now,encode_ns
                if encoded_now is None:
                    start=time.monotonic_ns();valid,encoded=cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,95]);assert valid
                    encoded_now=encoded.tobytes();encode_ns+=time.monotonic_ns()-start
                return encoded_now
            if result.boxes is not None and result.boxes.id is not None:
                for box,tid,confidence in zip(result.boxes.xyxy.cpu().tolist(),result.boxes.id.int().cpu().tolist(),result.boxes.conf.cpu().tolist()):
                    x1,y1,x2,y2=box;cx=(x1+x2)/2/w;cy=(y1+y2)/2/h
                    if not .34<cx<.75:continue
                    positions[tid]=cy;coords=clipped_box(box,w,h)
                    tracks.append({'source_frame':idx,'time_s':source_time,'track_id':tid,'axis_position':cy,'confidence':confidence,'x1':x1,'y1':y1,'x2':x2,'y2':y2})
                    if coords is None or not .25<=cy<=.75:continue
                    bx1,by1,bx2,by2=coords
                    if min(bx2-bx1,by2-by1)<128:continue
                    crop=frame[by1:by2,bx1:bx2];gray=cv2.cvtColor(crop,cv2.COLOR_BGR2GRAY)
                    resized=cv2.resize(gray,(max(1,round((bx2-bx1)*128/(by2-by1))),128),interpolation=cv2.INTER_AREA)
                    quality=float(cv2.Laplacian(resized,cv2.CV_64F).var());valid,png=cv2.imencode('.png',resized);assert valid
                    bank.consider(tid,Snapshot(idx,source_time,decoded_ns,coords,quality,confidence,png.tobytes()),jpeg)
            for event in counter.update(source_time,positions):capture(event,idx,time.monotonic_ns())
            advance_mock_rf(source_time);poll();sampled+=1;bank_max=max(bank_max,bank.bytes)
            frames.append({'source_frame':idx,'source_time_s':source_time,'decoded_wall_ns':decoded_ns,
                           'loop_start_wall_ns':loop_start,'detector_start_wall_ns':det_before,'detector_end_wall_ns':det_after,
                           'jpeg_encode_ns':encode_ns,'retained_snapshot_bytes':bank.bytes,'loop_end_wall_ns':time.monotonic_ns()})
            if sampled%400==0:print(json.dumps({'sampled':sampled,'source_time_s':source_time,'observed_events':len(events),'snapshot_bytes':bank.bytes}),flush=True)
        frontend_eof=time.monotonic_ns()
        for identity in pending:
            events[identity]['status']='UNRESOLVED_RF_WINDOW_CENSORED_AT_EOF';log(identity,events[identity]['status'])
        tasks.put(None,timeout=10);deadline=time.monotonic()+30
        while time.monotonic()<deadline and (child.is_alive() or any(r['status']=='QUEUED' for r in events.values())):
            try:record_result(results.get(timeout=.2))
            except queue.Empty:pass
            if not child.is_alive():poll();break
        child.join(timeout=1)
        if child.is_alive():child.terminate();child.join(timeout=5)
        poll()
        for row in events.values():
            if row['status']=='QUEUED':row['status']='UNRESOLVED_WORKER_DRAIN_TIMEOUT';log(row['event_id'],row['status'])
            (OUT/'events'/f'{row["event_id"]}.json').write_text(json.dumps(row,indent=2))
        for filename,rows in [('frames.csv',frames),('tracks.csv',tracks)]:
            with (OUT/filename).open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else []);writer.writeheader();writer.writerows(rows)
        event_rows=list(events.values());(OUT/'events.json').write_text(json.dumps(event_rows,indent=2))
        successful=[r for r in event_rows if r.get('worker_result',{}).get('status')=='COMPLETED']
        after_eof=sum(r['worker_result']['finished_wall_ns']>frontend_eof for r in successful)
        overlap=sum(any(max(r['worker_result']['started_wall_ns'],frame['loop_start_wall_ns'])<min(r['worker_result']['finished_wall_ns'],frame['loop_end_wall_ns']) for frame in frames) for r in successful)
        summary={'job_id':os.environ['SLURM_JOB_ID'],'status':'FUNCTIONAL_VIDEO_REPLAY_COMPLETE','protocol_sha256':sha(protocol_path),
                 'parent_pid':os.getpid(),'worker_pid':child.pid,'worker_exitcode':child.exitcode,'worker_ready':ready,
                 'source_sha256':p['source_video_sha256'],'source_frames_decoded':decoded,'sampled_detection_frames':sampled,
                 'excluded_terminal_frame':14008,'source_size':[w,h],'source_fps':fps,'detection_sampling_fps':5,
                 'observed_predicted_events':len(events),'A_to_B':sum(r['direction']=='A->B' for r in event_rows),'B_to_A':sum(r['direction']=='B->A' for r in event_rows),
                 'event_terminal_status_counts':dict(Counter(r['status'] for r in event_rows)),'actual_completed_identity_jobs':len(successful),
                 'true_model_query_forwards':sum(len(r['worker_result']['conditions']) for r in successful),
                 'jobs_completed_after_frontend_eof':after_eof,'jobs_overlapping_foreground_host_intervals':overlap,
                 'retained_snapshot_peak_bytes':bank.peak_bytes,'retained_snapshot_byte_limit':bank.max_bytes,'snapshot_evictions':bank.evictions,
                 'frontend_start_wall_ns':front_start,'frontend_eof_wall_ns':frontend_eof,'run_finished_wall_ns':time.monotonic_ns(),
                 'parent_maximum_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'worker_messages':messages,
                 'foreground_device':torch.cuda.get_device_name(0),'scope':p['scope'],
                 'latency_clock':'Host monotonic ns, source-frame decode availability; no camera exposure clock or board measurement',
                 'recognition_accuracy':None,'reference_labels':'No independent raw-video cow IDs or complete passage truth'}
        (OUT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in summary.items() if k not in ['worker_messages','worker_ready']},indent=2),flush=True)
        assert decoded==14008 and sampled==2802 and len(events)>0
        assert child.exitcode==0 and len(successful)>0 and all(len(r['worker_result']['conditions'])==5 for r in successful)
        assert bank.peak_bytes<=bank.max_bytes and overlap>0
        assert not any(r['status']=='PENDING_RF_WINDOW' or r['status']=='QUEUED' for r in event_rows)
    finally:
        cap.release();journal.close()
        if child.is_alive():child.terminate();child.join(timeout=5)
if __name__=='__main__':main()
