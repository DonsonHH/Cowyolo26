from pathlib import Path
from datetime import datetime,timezone
from PIL import Image
import json,hashlib,tarfile,gzip,importlib.util,sys,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def gz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
m=load(ROOT/'evidence/periodic_transfer.json');archive=ROOT/'periodic_delivery.tar.gz';assert archive.stat().st_size==m['bytes'] and sha(archive)==m['sha256']
OUT=ROOT/'periodic_delivery';OUT.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
 assert len(tar.getmembers())==m['members']
 for member in tar.getmembers():
  assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
  p=(OUT/member.name).resolve();assert p.is_relative_to(OUT.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(member).read())
for r in load(OUT/'periodic_manifest.json'):assert sha(OUT/r['file'])==r['sha256'] and (OUT/r['file']).stat().st_size==r['bytes']
assert sha(OUT/'run_protocol.json')==sha(ROOT/'protocol/periodic_v1.json')
for name in ['board_periodic_capture0.py','background_capture0_worker.py']:assert sha(OUT/name)==sha(ROOT/'tools'/name)
p=load(OUT/'run_protocol.json');s=load(OUT/'results/record.json');t=load(OUT/'results/terminal.json')
assert s['status']==t['status']=='ALL_THREE392_SLOT_LOSSLESS_CAPTURE_ENCODING_CONTROLS_COMPLETE' and t['record_sha256']==sha(OUT/'results/record.json')
assert s['actual_O8_forwards']==1170 and s['qualification_forwards']==8 and s['warmup_forwards']==6 and t['close_error'] is None
assert s['PL_after_sha256']==p['O8_bit_sha256'] and s['hardware_status']['error']=='0x0'
def module(name,file):
 spec=importlib.util.spec_from_file_location(name,file);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
scanner=module('capture0_counter_scanner',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py')
body=module('capture0_independent_body_input',PROJECT/'pynq_identity_ncnn_20261029/tools/ncnn_encoder_v3.py')
source=PROJECT/'pynq_rot192_eval_20261029/board_delivery/results_v2/original';oldraw=np.load(source/'all_raw.npy',mmap_mode='r')
oldtrace=gz(source/'stride5_counter_trace.json.gz');cases=[];rawchecks=ticks=paths=0
for case in p['cases']:
 folder=OUT/'results'/case;rows=load(folder/'timing_rows.json');skips=load(folder/'skipped_slots.json');trace=gz(folder/'counter_trace.json.gz')
 summary=next(r for r in s['cases'] if r['case']==case);t0=summary['clock_start_monotonic_ns'];period=p['period_ns']
 assert sorted([r['slot'] for r in rows]+[r['slot'] for r in skips])==list(range(392))
 for row in rows:
  assert row['frame0']==8915+row['slot']*5 and row['release_monotonic_ns']==t0+period*row['slot']
  assert row['release_monotonic_ns']<=row['started_monotonic_ns']<=row['completed_monotonic_ns']
  assert row['deadline_met']==(row['completed_monotonic_ns']<=row['release_monotonic_ns']+period)
  assert row['release_to_count_ms']==(row['completed_monotonic_ns']-row['release_monotonic_ns'])/1e6
  assert row['processing_ms']==(row['completed_monotonic_ns']-row['started_monotonic_ns'])/1e6
 for row in skips:assert row['skip_observed_monotonic_ns']>=t0+period*(row['slot']+1)
 assert summary['processed_frames']==len(rows) and summary['skipped_slots']==len(skips) and summary['deadline_misses']==sum(not r['deadline_met'] for r in rows)
 assert summary['P95_release_to_count_ms']==np.quantile([r['release_to_count_ms'] for r in rows],.95)
 with np.load(folder/'actual_raw.npz') as a:
  assert a['frame0'].tolist()==[r['frame0'] for r in rows]
  for frame,raw in zip(a['frame0'],a['raw']):assert oldraw[frame//5].tobytes()==raw.tobytes();rawchecks+=1
 assert [r['frame0'] for r in trace['observations']]==list(range(0,8915,5))+[r['frame0'] for r in rows];ticks+=len(trace['observations'])
 for key in ['observations','post_tracker','confirmed_only_events','handoff_events']:assert [r for r in trace[key] if r['frame0']<8915]==[r for r in oldtrace[key] if r['frame0']<8915]
 for kind,admit in [('confirmed_only_events',False),('handoff_events',True)]:
  events,_=scanner.batch_events(trace['observations'],admit);assert events==trace[kind];paths+=1
  if admit:assert [e for e in events if 8912<=e['frame0']<=10873]==summary['periodic_events']
 cases.append({k:v for k,v in summary.items() if k!='periodic_events'})
with np.load(PROJECT/'pynq_identity_ncnn_20261029/board_delivery/vectors_results_v3/all_normalized_features.npz') as a:gallery=a['new_gallery'].astype(float)
galleryrows=load(PROJECT/'pynq_identity_ncnn_20261029/input/images.json')['new_gallery'];backend_summaries=[];alljobs=0;pairphotos=0;pauses_checked=0
for case,priorroot,priorcase in [('foreground_with_identity','pynq_periodic_joint_20261030','foreground_with_identity'),('foreground_idle_identity','pynq_idle_control_20261030','foreground_idle_identity')]:
 folder=OUT/'results'/case;bg=folder/'background';b=load(bg/'record.json');bt=load(bg/'terminal.json');enqueued=load(folder/'enqueued_identity_jobs.json')
 assert b['status']==bt['status']=='ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE' and bt['record_sha256']==sha(bg/'record.json')
 assert len(b['jobs'])==b['model_forwards']==len(enqueued)==11 and len(b['warmups'])==1 and b['PNG_compress_level']==0
 intervals=load(folder/'worker_pause_intervals.json');rows=load(folder/'timing_rows.json')
 if case=='foreground_idle_identity':
  assert len(intervals)==len(rows)==388
  for interval,row in zip(intervals,rows):
   assert interval['slot']==row['slot'] and interval['pause_acknowledged_monotonic_ns']<=row['started_monotonic_ns']<=row['completed_monotonic_ns']<=interval['resume_sent_monotonic_ns'];pauses_checked+=1
 else:assert intervals==[]
 prior=PROJECT/priorroot/'delivery/results'/priorcase/'background';priorjobs=load(prior/'record.json')['jobs'];same_frame=0
 for job,request in zip(b['jobs'],enqueued):
  assert job['source_frame0']==request['source_frame0'] and job['event']==request['event']
  image=PROJECT/'pynq_periodic_joint_20261030/camera_delivery/highres'/('f'+str(job['source_frame0']).zfill(5)+'.jpg')
  with Image.open(image) as im:im.load();native=im.convert('RGB')
  x1,y1,x2,y2=request['box_native_xyxy'];crop=[max(0,math.floor(x1-870)),max(0,math.floor(y1)),min(1050,math.ceil(x2-870)),min(1440,math.ceil(y2))]
  expected=native.crop(crop).transpose(Image.Transpose.ROTATE_270)
  photo=bg/job['photo_file'];assert sha(photo)==job['photo_sha256']
  with Image.open(photo) as im:im.load();assert im.convert('RGB').tobytes()==expected.tobytes()
  tensor=body.body_tensor(expected)
  with np.load(bg/job['vector_file']) as a:
   assert a['input'].tobytes()==tensor.tobytes() and hashlib.sha256(a['raw'].tobytes()).hexdigest()==job['raw_feature_sha256']
   feature=a['raw'].astype(float)/np.linalg.norm(a['raw'].astype(float));assert np.max(np.abs(feature-a['normalized']))<1e-7
   dots=a['normalized'].astype(float)@gallery.T;scores=[max(dots[i] for i,row in enumerate(galleryrows) if row['identity']==label) for label in p['registered_IDs']]
   winner=int(np.argmax(scores));assert job['predicted_id']==p['registered_IDs'][winner] and abs(job['similarity']-scores[winner])<1e-12 and job['accepted']==(scores[winner]>=p['fixed_identity_threshold'])
  candidates=[j for j in priorjobs if j['source_frame0']==job['source_frame0'] and j['native_current_tracker_box']==job['native_current_tracker_box']]
  if candidates:
   before=candidates[0]
   with Image.open(prior/before['photo_file']) as im:im.load();assert im.convert('RGB').tobytes()==expected.tobytes()
   assert before['input_tensor_sha256']==job['input_tensor_sha256']
   with np.load(prior/before['vector_file']) as a, np.load(bg/job['vector_file']) as z:assert a['raw'].tobytes()==z['raw'].tobytes()
   pairphotos+=1;same_frame+=1
  alljobs+=1
 backend_summaries.append({'case':case,'actual_jobs':11,'PNG_level':0,'same_frame_same_box_photo_pixels_inputs_and_raw_bytes_exact_to_prior_level6_jobs':same_frame,
  'mean_photo_crop_and_save_elapsed_ms':float(np.mean([j['runtime_native_crop_and_photo_save_ms'] for j in b['jobs']])),
  'max_queue_ms':max(j['queue_wait_ms'] for j in b['jobs']),'max_enqueue_to_result_ms':max(j['enqueue_to_result_ms'] for j in b['jobs']),
  'saved_photo_bytes':sum((bg/j['photo_file']).stat().st_size for j in b['jobs']),'accepted_provisional_predictions':sum(j['accepted'] for j in b['jobs'])})
assert rawchecks==1170 and ticks==6519 and paths==6 and alljobs==22
r={'status':'ALL_THREE1170_O8_FRAMES6_EVENT_PATHS22_ACTUAL_IDENTITY_JOBS_AND_LOSSLESS_CAPTURE_PARITY_VERIFIED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'actual_O8_timed_forwards':1170,'O8_qualification_forwards':8,'O8_warmups':6,
 'cases':cases,'counter_observation_ticks_including_history':ticks,'independent_event_paths':paths,'actual_background_identity_jobs':22,'identity_warmups':2,
 'all22_runtime_photo_and_tensor_reconstructed':True,'same_frame_same_box_prior_photo_input_and_feature_exact_pairs':pairphotos,
 'worker_pause_intervals_verified':pauses_checked,'backgrounds':backend_summaries,'actual_both_networks_on_same_PYNQ':True,
 'zero_deadline_misses_proven':False,'camera_and_RFID_are_replay_and_simulation':True,'identity_accuracy_newly_proven':False,
 'each_condition_single_run_not_statistical_replicates':True,'whole_goal_complete':False,'archive_sha256':sha(archive)}
file=ROOT/'results/periodic_verification.json';assert not file.exists();file.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
