from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
from collections import defaultdict
import json,gzip,hashlib,tarfile,math,importlib.util,sys
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def gz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mod(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
meta=load(ROOT/'evidence/transfer.json');a=ROOT/'joint_results_delivery_v1.tar.gz'
assert sha(a)==meta['sha256'] and a.stat().st_size==meta['bytes']
OUT=ROOT/'delivery';OUT.mkdir(exist_ok=False)
with tarfile.open(a) as tar:
    members=tar.getmembers();assert len(members)==meta['members']
    for member in members:
        name=PurePosixPath(member.name);assert member.isfile() and not name.is_absolute() and '..' not in name.parts
        f=OUT.joinpath(*name.parts).resolve();assert f.is_relative_to(OUT.resolve()) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(member).read())
for r in load(OUT/'result_manifest.json'):
    f=OUT/r['file'];assert sha(f)==r['sha256'] and f.stat().st_size==r['bytes']
for relative,local in [('run_protocol.json','protocol/run_v1.json'),('board_joint_repeats.py','tools/board_joint_repeats.py'),('background_capture0_worker.py','tools/background_capture0_worker.py')]:assert sha(OUT/relative)==sha(ROOT/local)
p=load(OUT/'run_protocol.json');s=load(OUT/'results/record.json');t=load(OUT/'results/terminal.json');final=load(OUT/'final_state.json')
assert s['status']==t['status']=='ALL_SIX392_SLOT_MOSAIC192_SAME_BOARD_REPEATS_COMPLETE' and t['record_sha256']==sha(OUT/'results/record.json')
assert s['qualification_forwards']==8 and s['warmup_forwards']==12 and t['close_error'] is None and not final['proc_exists']
assert len(final['children'])==4 and not any(r['proc_exists'] for r in final['children'])
assert s['PL_after_sha256']==final['PL_bit_sha256']==p['O8_bit_sha256'] and s['hardware_status']['error']=='0x0'
scanner=mod('mosaic_joint_independent_runs',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py')
body=mod('mosaic_joint_independent_body',PROJECT/'pynq_identity_ncnn_20261029/tools/ncnn_encoder_v3.py')
source=PROJECT/'pynq_mosaic192_eval_20261030/board_delivery/results/original'
oldraw=np.load(source/'all_raw.npy',mmap_mode='r');oldtrace=gz(source/'stride5_counter_trace.json.gz')
with np.load(PROJECT/'pynq_identity_ncnn_20261029/board_delivery/vectors_results_v3/all_normalized_features.npz') as ar:gallery=ar['new_gallery'].astype(float)
galleryrows=load(PROJECT/'pynq_identity_ncnn_20261029/input/images.json')['new_gallery']
rawchecks=ticks=paths=jobs=warmups=pauses=0;cases=[];backgrounds=[]
for run,summary in zip(p['runs'],s['cases']):
    assert summary['run']==run['run'] and summary['case']==run['policy'] and summary['repeat']==run['repeat']
    folder=OUT/'results'/run['run'];rows=load(folder/'timing_rows.json');skips=load(folder/'skipped_slots.json');trace=gz(folder/'counter_trace.json.gz')
    t0=summary['clock_start_monotonic_ns'];period=p['period_ns']
    assert sorted([r['slot'] for r in rows]+[r['slot'] for r in skips])==list(range(392))
    for r in rows:
        assert r['frame0']==8915+5*r['slot'] and r['release_monotonic_ns']==t0+period*r['slot']
        assert r['release_monotonic_ns']<=r['started_monotonic_ns']<=r['completed_monotonic_ns']
        assert r['deadline_met']==(r['completed_monotonic_ns']<=r['release_monotonic_ns']+period)
        assert r['release_to_count_ms']==(r['completed_monotonic_ns']-r['release_monotonic_ns'])/1e6
        assert r['processing_ms']==(r['completed_monotonic_ns']-r['started_monotonic_ns'])/1e6
        assert abs(r['model_ms']+r['after_model_to_count_ms']-r['processing_ms'])<1e-8
    for r in skips:assert r['skip_observed_monotonic_ns']>=t0+period*(r['slot']+1)
    assert summary['processed_frames']==len(rows) and summary['skipped_slots']==len(skips) and summary['deadline_misses']==sum(not r['deadline_met'] for r in rows)
    assert summary['mean_processing_ms']==np.mean([r['processing_ms'] for r in rows])
    assert summary['P95_release_to_count_ms']==np.quantile([r['release_to_count_ms'] for r in rows],.95)
    assert summary['processed_per_second_over_offered_duration']==len(rows)/78.4
    with np.load(folder/'actual_raw.npz') as ar:
        assert ar['frame0'].tolist()==[r['frame0'] for r in rows]
        for frame,raw in zip(ar['frame0'],ar['raw']):assert raw.tobytes()==oldraw[frame//5].tobytes();rawchecks+=1
    assert [r['frame0'] for r in trace['observations']]==list(range(0,8915,5))+[r['frame0'] for r in rows]
    for key in ['observations','post_tracker','confirmed_only_events','handoff_events']:
        assert [r for r in trace[key] if r['frame0']<8915]==[r for r in oldtrace[key] if r['frame0']<8915]
    byframe=defaultdict(list)
    for r in trace['post_tracker']:byframe[r['frame0']].append(r)
    for row in trace['observations']:
        positions={};ids=set()
        for post in byframe[row['frame0']]:
            tid=post['track_id']
            if tid is None:continue
            ids.add(tid);x,y,z,w=post['xyxy'];cx=(x+z)/(2*2560);cy=(y+w)/(2*1440)
            if .34<cx<.75:positions[str(tid)]=cy
        assert row['confirmed_positions']==positions and row['confirmed_IDs']==sorted(ids)
    ticks+=len(trace['observations'])
    for kind,admit in [('confirmed_only_events',False),('handoff_events',True)]:
        events,_=scanner.batch_events(trace['observations'],admit);assert events==trace[kind];paths+=1
        if admit:
            events=[e for e in events if 8912<=e['frame0']<=10873]
            assert events==summary['periodic_events'] and summary['source_down_count']==sum(e['direction']=='A->B' for e in events)
            assert summary['source_up_count']==sum(e['direction']=='B->A' for e in events)
    cases.append({k:v for k,v in summary.items() if k!='periodic_events'})
    intervals=load(folder/'worker_pause_intervals.json')
    if run['policy']=='foreground_only':
        assert intervals==[] and summary['actual_background_jobs']==0;continue
    bg=folder/'background';b=load(bg/'record.json');bt=load(bg/'terminal.json');enqueued=load(folder/'enqueued_identity_jobs.json')
    assert bt['record_sha256']==sha(bg/'record.json') and b['status']==bt['status']=='ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE'
    assert len(b['jobs'])==b['model_forwards']==len(enqueued)==summary['actual_background_jobs']
    assert b['PNG_compress_level']==0 and len(b['warmups'])==1;warmups+=1
    if run['policy']=='foreground_idle_identity':
        assert len(intervals)==len(rows)
        for interval,row in zip(intervals,rows):
            assert interval['slot']==row['slot'] and interval['pause_acknowledged_monotonic_ns']<=row['started_monotonic_ns']<=row['completed_monotonic_ns']<=interval['resume_sent_monotonic_ns'];pauses+=1
    else:assert intervals==[]
    for job,request in zip(b['jobs'],enqueued):
        assert job['event']==request['event'] and job['source_frame0']==request['source_frame0'] and job['identity_reference_available'] is False
        assert request['event'] in summary['periodic_events']
        assert job['started_monotonic_ns']>=job['enqueued_monotonic_ns']>=job['release_monotonic_ns']
        assert job['queue_wait_ms']==(job['started_monotonic_ns']-job['enqueued_monotonic_ns'])/1e6
        assert job['enqueue_to_result_ms']==(job['completed_monotonic_ns']-job['enqueued_monotonic_ns'])/1e6
        eventbox=next(r for r in byframe[job['source_frame0']] if r['track_id']==job['event']['track_id'])
        assert eventbox['xyxy']==request['box_native_xyxy']==job['native_current_tracker_box']
        highres=PROJECT/'pynq_periodic_joint_20261030/camera_delivery/highres'/('f'+str(job['source_frame0']).zfill(5)+'.jpg')
        with Image.open(highres) as im:im.load();native=im.convert('RGB')
        x,y,z,w=request['box_native_xyxy'];crop=[max(0,math.floor(x-870)),max(0,math.floor(y)),min(1050,math.ceil(z-870)),min(1440,math.ceil(w))]
        expected=native.crop(crop).transpose(Image.Transpose.ROTATE_270)
        photo=bg/job['photo_file'];assert sha(photo)==job['photo_sha256'] and job['native_source_crop_xyxy']==crop
        with Image.open(photo) as im:im.load();assert im.convert('RGB').tobytes()==expected.tobytes()
        tensor=body.body_tensor(expected)
        assert sha(bg/job['vector_file'])==job['vector_sha256']
        with np.load(bg/job['vector_file']) as ar:
            assert tensor.tobytes()==ar['input'].tobytes() and hashlib.sha256(tensor.tobytes()).hexdigest()==job['input_tensor_sha256']
            assert hashlib.sha256(ar['raw'].tobytes()).hexdigest()==job['raw_feature_sha256']
            feature=ar['raw'].astype(float)/np.linalg.norm(ar['raw'].astype(float));assert np.max(np.abs(feature-ar['normalized']))<1e-7
            dots=ar['normalized'].astype(float)@gallery.T
            scores=np.array([max(dots[i] for i,r in enumerate(galleryrows) if r['identity']==label) for label in p['registered_IDs']])
            assert np.max(np.abs(scores-ar['scores']))<1e-12
            winner=int(np.argmax(scores));assert p['registered_IDs'][winner]==job['predicted_id'] and abs(float(scores[winner])-job['similarity'])<1e-12
            assert bool(scores[winner]>=p['fixed_identity_threshold'])==job['accepted']
        jobs+=1
    backgrounds.append({'run':run['run'],'policy':run['policy'],'repeat':run['repeat'],'actual_jobs':len(b['jobs']),
        'accepted_provisional_predictions':sum(j['accepted'] for j in b['jobs']),
        'max_queue_wait_ms':max((j['queue_wait_ms'] for j in b['jobs']),default=0.),'max_enqueue_to_result_ms':max((j['enqueue_to_result_ms'] for j in b['jobs']),default=0.),
        'mean_network_elapsed_ms':float(np.mean([j['actual_identity_network_ms'] for j in b['jobs']])) if b['jobs'] else None,
        'mean_network_CPU_ms':float(np.mean([j['identity_network_process_CPU_ms'] for j in b['jobs']])) if b['jobs'] else None,
        'saved_photo_bytes':sum((bg/j['photo_file']).stat().st_size for j in b['jobs'])})
assert len(cases)==6 and rawchecks==s['actual_O8_forwards'] and ticks==6*1783+rawchecks and paths==12 and warmups==4
result={'status':'SIX_REAL_PYNQ_REPEATS_ALL_RAW_EVENT_PHOTO_TENSOR_RETRIEVAL_AND_PAUSE_RECORDS_VERIFIED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'actual_O8_timed_forwards':rawchecks,'actual_O8_qualification_forwards':8,'actual_O8_warmups':12,
    'counter_observation_ticks_with_history':ticks,'counter_paths':12,'cases':cases,'actual_background_identity_jobs':jobs,'identity_warmups':4,
    'backgrounds':backgrounds,'pause_windows_verified':pauses,'all_runtime_photos_inputs_features_scores_recomputed':True,
    'both_networks_run_on_same_PYNQ':True,'input_is_public_replay_RFID_is_simulated':True,
    'permanent_identity_accuracy_newly_proven':False,'repeats_are_same_source_not_independent_sessions':True,
    'parent_and_four_background_workers_terminal_absent':True,'new_training_updates':0,'new_independent_test':False,'whole_goal_complete':False,
    'archive_sha256':meta['sha256'],'archive_members':len(members)}
f=ROOT/'results/independent_verification.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
