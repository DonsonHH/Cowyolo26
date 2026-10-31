"""Frozen-native-observation capture and a real independent CPU query worker."""
from pathlib import Path
from collections import defaultdict,Counter
import csv,hashlib,io,json,multiprocessing,os,queue,resource,socket,sys,time
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/confirmed12_capture_identity_20261029');PROJECT=ROOT.parent
sys.path.insert(0,str(ROOT/'input'))
from snapshot_bank import SnapshotBank,Snapshot,clipped_box
from confirmation_counter import ConfirmationHandoffCounter
from identity_worker import worker_main
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):
    assert not p.exists(),p
    p.write_text(json.dumps(value,indent=2)+'\n')
def atomic(p,data):
    temporary=p.with_name(p.name+'.partial');assert not p.exists() and not temporary.exists()
    temporary.write_bytes(data);temporary.replace(p)
def csvsave(p,rows):
    with p.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else []);writer.writeheader();writer.writerows(rows)

def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    import cv2,numpy as np
    from PIL import Image
    cv2.setNumThreads(1)
    p=load(ROOT/'protocol/chain_v1.json');assert sha(p['source_video'])==p['source_video_sha256']
    assert sha(ROOT/'tools/identity_worker.py')==p['identity_worker_sha256']
    assert sha(PROJECT/'identity_training/tools/training_primitives.py')==p['body_transform_sha256']
    for name,digest in p['input_module_sha256'].items():assert sha(ROOT/'input'/name)==digest
    for row in p['cache_files']:assert Path(row['path']).stat().st_size==row['bytes'] and sha(row['path'])==row['sha256']
    by_frame=defaultdict(list)
    with Path(next(r['path'] for r in p['cache_files'] if r['name']=='post_tracker_boxes.csv')).open(newline='') as f:
        for row in csv.DictReader(f):by_frame[int(row['frame0'])].append(row)
    observations=load(next(r['path'] for r in p['cache_files'] if r['name']=='observations.json'))
    obs_by_frame={r['frame0']:r for r in observations};assert len(observations)==2175
    out=ROOT/'results/replay';out.mkdir(parents=True,exist_ok=False)
    for folder in ['photos','quality','events']:(out/folder).mkdir()
    protocol={**p,'identity_gallery_export_path':str(out/'gallery_vectors.json')}
    ctx=multiprocessing.get_context('spawn');tasks=ctx.Queue(maxsize=p['worker_queue_capacity']);results=ctx.Queue(maxsize=p['worker_result_capacity'])
    worker=ctx.Process(target=worker_main,args=(tasks,results,protocol,str(PROJECT)));worker.start()
    cap=None;journal=None
    try:
        ready=results.get(timeout=p['worker_ready_timeout_seconds']);assert ready['kind']=='ready',ready
        assert ready['device']=='cpu' and ready['conditions']==5 and ready['pid']!=os.getpid()
        save(out/'worker_ready.json',ready)
        cap=cv2.VideoCapture(p['source_video']);assert cap.isOpened()
        assert (int(cap.get(3)),int(cap.get(4)),cap.get(5))==(2560,1440,25.)
        bank=SnapshotBank();counter=ConfirmationHandoffCounter(**p['counter'])
        events={};pending=[];frames=[];candidate_inputs=[];all_count_events=[];messages=[];max_inflight=0
        journal=(out/'transitions.jsonl').open('w');current_frame=0;started=time.monotonic_ns()
        def log(event_id,transition,**fields):
            item={'event_id':event_id,'transition':transition,'source_clock_frame0':current_frame,'wall_ns':time.monotonic_ns(),**fields}
            journal.write(json.dumps(item)+'\n');journal.flush();os.fsync(journal.fileno())
        def persist(row):
            path=out/'events'/(row['event_id']+'.json');temp=path.with_name(path.name+'.partial')
            temp.write_text(json.dumps(row,indent=2)+'\n');temp.replace(path)
        def receive(message):
            messages.append(message)
            if message['kind']=='fatal':raise RuntimeError('CPU worker reported fatal: '+str(message))
            if message['kind']!='result':return
            row=events[message['event_id']];assert row['status']=='QUEUED'
            message['parent_received_wall_ns']=time.monotonic_ns();row['worker_result']=message
            if message['status']=='COMPLETED':
                assert len(message['conditions'])==5
                row['status']='CANDIDATE_THRESHOLD_PASSED_UNVERIFIED' if any(c['passes_frozen_threshold'] for c in message['conditions']) else 'ALL_CONDITIONS_REJECTED'
            else:row['status']='UNRESOLVED_'+message['status']
            assert all(c['verified_identity'] is False for c in message['conditions']);row['verified_identity']=False
            persist(row);log(row['event_id'],row['status'],worker_status=message['status'])
        def poll():
            while True:
                try:message=results.get_nowait()
                except queue.Empty:break
                receive(message)
        def capture(event):
            identity=f'E{len(events)+1:03d}_f{event["frame0"]}_tid{event["track_id"]}'
            choices=bank.take(event['track_id'],event['time_s'])
            row={'event_id':identity,'frame0':event['frame0'],'source_time_s':event['time_s'],'track_id':event['track_id'],'direction':event['direction'],
                 'event_observed_wall_ns':time.monotonic_ns(),'source_identity_reference':None,'verified_identity':False,
                 'rf_status':p['rf_mode'],'rf_deadline_source_s':event['time_s']+p['rf_window_source_seconds'],
                 'status':'PENDING_RF_WINDOW','quality_candidates':[]}
            events[identity]=row;log(identity,'EVENT_OBSERVED',counter_event=event)
            for i,(snapshot,jpeg) in enumerate(choices):
                dest=out/'quality'/f'{identity}_choice{i+1}_f{snapshot.frame}.png';atomic(dest,snapshot.quality_png)
                row['quality_candidates'].append({'frame0':snapshot.frame,'source_time_s':snapshot.source_time,
                    'decoded_wall_ns':snapshot.decoded_wall_ns,'box':list(snapshot.box),'quality':snapshot.quality,'confidence':snapshot.confidence,
                    'quality_path':dest.relative_to(out).as_posix(),'quality_sha256':sha(dest)})
            if not choices:
                row['status']='UNRESOLVED_NO_SNAPSHOT';persist(row);log(identity,row['status']);return
            snapshot,jpeg=choices[0];dest=out/'photos'/(identity+'_native.jpg');atomic(dest,jpeg)
            with Image.open(io.BytesIO(jpeg)) as im:
                im=im.convert('RGB');assert im.size==(2560,1440);crop=im.crop(snapshot.box)
                oriented=crop.transpose(Image.Transpose.ROTATE_90 if event['direction']=='A->B' else Image.Transpose.ROTATE_270)
            crop_path=out/'photos'/(identity+'_crop.png');oriented_path=out/'photos'/(identity+'_oriented.png')
            for file,image in [(crop_path,crop),(oriented_path,oriented)]:
                buffer=io.BytesIO();image.save(buffer,format='PNG');atomic(file,buffer.getvalue())
            row['selected_snapshot']={**row['quality_candidates'][0],
                'native_path':dest.relative_to(out).as_posix(),'native_sha256':sha(dest),'native_dimensions':[2560,1440],
                'crop_path':crop_path.relative_to(out).as_posix(),'crop_sha256':sha(crop_path),'crop_dimensions':list(crop.size),
                'oriented_path':oriented_path.relative_to(out).as_posix(),'oriented_sha256':sha(oriented_path),'oriented_dimensions':list(oriented.size),
                'rotation_CCW_degrees':90 if event['direction']=='A->B' else 270}
            row['snapshot_saved_wall_ns']=time.monotonic_ns();pending.append(identity);persist(row)
            log(identity,'SNAPSHOT_SAVED',selected_frame0=snapshot.frame)
        def advance_rf(source_time):
            nonlocal max_inflight
            for identity in list(pending):
                row=events[identity]
                if source_time<row['rf_deadline_source_s']:continue
                pending.remove(identity);now=time.monotonic_ns()
                row.update(rf_closed_frame0=current_frame,rf_closed_source_time_s=source_time,enqueue_wall_ns=now,
                           deadline_wall_ns=now+round(p['worker_deadline_wall_seconds']*1e9))
                selected=row['selected_snapshot'];job={'event_id':identity,'oriented_crop_path':str(out/selected['oriented_path']),
                    'oriented_crop_sha256':selected['oriented_sha256'],'deadline_wall_ns':row['deadline_wall_ns']}
                if not worker.is_alive():row['status']='UNRESOLVED_WORKER_NOT_ALIVE'
                else:
                    try:tasks.put_nowait(job);row['status']='QUEUED'
                    except queue.Full:row['status']='UNRESOLVED_QUEUE_CAPACITY'
                max_inflight=max(max_inflight,sum(e['status']=='QUEUED' for e in events.values()))
                persist(row);log(identity,row['status'],mock_RF_closed_at_source_s=source_time)
        for frame in range(p['decode_end_frame0_exclusive']):
            current_frame=frame;loop_start=time.monotonic_ns();ok,image=cap.read();assert ok,frame
            if frame%p['stride']:continue
            decoded_ns=time.monotonic_ns();source_time=frame/25;bank.advance(source_time);poll()
            observation=obs_by_frame[frame];positions={};active=set();tentative={int(k):v for k,v in observation['tentative_positions'].items()}
            for box in by_frame[frame]:
                if not box['track_id']:continue
                tid=int(box['track_id']);active.add(tid)
                x1,y1,x2,y2=[float(box[k]) for k in ['x1','y1','x2','y2']];cx=(x1+x2)/5120;cy=(y1+y2)/2880
                if not .34<cx<.75:continue
                positions[tid]=cy
            assert positions=={int(k):v for k,v in observation['confirmed_positions'].items()} and active==set(observation['confirmed_IDs'])
            encoded=None
            def jpeg_supplier():
                nonlocal encoded
                if encoded is None:
                    success,data=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,95]);assert success;encoded=data.tobytes()
                return encoded
            if 8912<=frame<10874:
                for box in by_frame[frame]:
                    if not box['track_id']:continue
                    tid=int(box['track_id'])
                    if tid not in positions or not .25<=positions[tid]<=.75:continue
                    native=[float(box[k]) for k in ['x1','y1','x2','y2']];coords=clipped_box(native,2560,1440)
                    if coords is None or min(coords[2]-coords[0],coords[3]-coords[1])<128:continue
                    x1,y1,x2,y2=coords;gray=cv2.cvtColor(image[y1:y2,x1:x2],cv2.COLOR_BGR2GRAY)
                    thumb=cv2.resize(gray,(max(1,round((x2-x1)*128/(y2-y1))),128),interpolation=cv2.INTER_AREA)
                    sharpness=float(cv2.Laplacian(thumb,cv2.CV_64F).var());valid,data=cv2.imencode('.png',thumb);assert valid
                    accepted=bank.consider(tid,Snapshot(frame,source_time,decoded_ns,coords,sharpness,float(box['confidence']),data.tobytes()),jpeg_supplier)
                    candidate_inputs.append({'frame0':frame,'track_id':tid,'box_x1':x1,'box_y1':y1,'box_x2':x2,'box_y2':y2,
                        'quality':sharpness,'confidence':float(box['confidence']),'consider_result':accepted,
                        'quality_png_bytes':len(data),'bank_bytes_after_consider':bank.bytes})
            outputs=counter.update(source_time,positions,tentative,active)
            assert counter.last_acceptances==observation['accepted_history']
            for event in outputs:
                event['frame0']=frame;all_count_events.append(event)
                if 8912<=frame<10874:capture(event)
            advance_rf(source_time);poll()
            frames.append({'frame0':frame,'source_time_s':source_time,'loop_start_wall_ns':loop_start,'decoded_wall_ns':decoded_ns,
                           'retained_bank_bytes':bank.bytes,'loop_end_wall_ns':time.monotonic_ns()})
        eof=time.monotonic_ns();cap.release();cap=None
        assert all_count_events==p['expected_events'] and len(events)==12 and len(frames)==2175
        for identity in pending:
            row=events[identity];row['status']='UNRESOLVED_RF_WINDOW_EOF_CENSORED';persist(row);log(identity,row['status'])
        tasks.put(None,timeout=10);end=time.monotonic()+p['worker_drain_wall_seconds']
        while time.monotonic()<end and (worker.is_alive() or any(r['status']=='QUEUED' for r in events.values())):
            try:receive(results.get(timeout=.2))
            except queue.Empty:pass
            if not worker.is_alive():poll();break
        worker.join(timeout=1)
        if worker.is_alive():worker.terminate();worker.join(timeout=5)
        poll()
        for row in events.values():
            if row['status']=='QUEUED':row['status']='UNRESOLVED_WORKER_DRAIN_TIMEOUT';log(row['event_id'],row['status'])
            persist(row)
        assert worker.exitcode==0
        event_rows=list(events.values());save(out/'events.json',event_rows);save(out/'worker_messages.json',messages)
        csvsave(out/'frontend_ticks.csv',frames);csvsave(out/'snapshot_candidate_inputs.csv',candidate_inputs)
        complete=[r for r in event_rows if r.get('worker_result',{}).get('status')=='COMPLETED']
        forwarded=[r for r in event_rows if len(r.get('worker_result',{}).get('conditions',[]))==5]
        passing={c['name']:sum(q['passes_frozen_threshold'] for e in forwarded for q in e['worker_result']['conditions'] if q['condition']==c['name']) for c in p['identity']['conditions']}
        overlap=sum(any(max(e['worker_result']['started_wall_ns'],f['loop_start_wall_ns'])<min(e['worker_result']['finished_wall_ns'],f['loop_end_wall_ns']) for f in frames) for e in forwarded)
        summary={'status':'ACCEPTED12_CACHED_COUNTER_NATIVE_CAPTURE_AND_REAL_CPU_IDENTITY_CHAIN_COMPLETE','job_id':os.environ['SLURM_JOB_ID'],
            'protocol_sha256':sha(ROOT/'protocol/chain_v1.json'),'source_sha256':p['source_video_sha256'],
            'source_frames_decoded':10874,'cached_observation_ticks':2175,'counter_events_exact':True,
            'event_count':len(event_rows),'native_photos':sum('selected_snapshot' in r for r in event_rows),
            'task_terminal_status_counts':dict(Counter(e['status'] for e in event_rows)),'worker_completed_jobs':len(complete),
            'true_query_forwards':sum(len(r['worker_result']['conditions']) for r in forwarded),'threshold_pass_counts_by_condition':passing,
            'jobs_finishing_after_frontend_EOF':sum(e['worker_result']['finished_wall_ns']>eof for e in forwarded),
            'jobs_overlapping_cached_frontend_host_intervals':overlap,'max_observed_inflight_including_service':max_inflight,
            'snapshot_bank_peak_bytes':bank.peak_bytes,'snapshot_bank_byte_limit':bank.max_bytes,'snapshot_bank_evictions':bank.evictions,
            'candidate_input_rows':len(candidate_inputs),'gallery_images':30,'gallery_identities':6,
            'parent_pid':os.getpid(),'worker_pid':worker.pid,'worker_exit_code':worker.exitcode,
            'frontend_start_wall_ns':started,'frontend_EOF_wall_ns':eof,'finish_wall_ns':time.monotonic_ns(),
            'parent_peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'verified_source_cow_identities':0,
            'source_identity_accuracy':None,'foreground_detector_ran_in_this_job':False,
            'new_detector_forwards':0,'new_training_updates':0,'FPGA_execution_verified':False,'whole_goal_complete':False}
        assert not any(r['status'] in ['PENDING_RF_WINDOW','QUEUED'] for r in event_rows)
        assert bank.peak_bytes<=bank.max_bytes and len(forwarded)>0
        save(out/'summary.json',summary);print(json.dumps(summary),flush=True)
    finally:
        if cap is not None:cap.release()
        if journal is not None:journal.close()
        if worker.is_alive():worker.terminate();worker.join(timeout=5)
if __name__=='__main__':main()
