from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json,gzip,hashlib,math,importlib.util,sys
from PIL import Image
import numpy as np
from independent_geometry import verify_selection
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OUT=ROOT/'delivery'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def gz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mod(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
p=load(OUT/'run_protocol.json');s=load(OUT/'results/record.json');t=load(OUT/'results/terminal.json');final=load(OUT/'final_board_state.json')
assert sha(OUT/'run_protocol.json')==sha(ROOT/'protocol/run_v1.json')=='17e08b19b38d438351e005ecc6fa90256f65b7ec8f780aa517449d7c3856af4c'
assert s['status']==t['status']=='ALL4_ACTUAL_COUNT_TRIGGER_OLD_NEW_NEW_OLD_ASYNC_CAUSAL_IDENTITY_RUNS_COMPLETE' and t['record_sha256']==sha(OUT/'results/record.json')
assert s['qualification_forwards']==8 and s['warmup_forwards']==8 and t['close_error'] is None and final['parent_PID']==t['PID'] and final['all_runtime_hashes_match']
assert len(final['children'])==4 and not any(r['proc_exists'] for r in final['children'])
assert s['PL_after_sha256']==final['PL_SHA256']==p['O8_bit_sha256'] and s['hardware_status']['error']=='0x0'
scanner=mod('causal_independent_counter',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py')
body=mod('causal_independent_body',PROJECT/'pynq_identity_ncnn_20261029/tools/ncnn_encoder_v3.py')
source=PROJECT/'pynq_mosaic192_eval_20261030/board_delivery/results/original';oldraw=np.load(source/'all_raw.npy',mmap_mode='r');oldtrace=gz(source/'stride5_counter_trace.json.gz')
camera=PROJECT/'pynq_periodic_joint_20261030/camera_delivery';camera_rows={r['frame0']:r for r in load(camera/'manifest.json')}
with np.load(PROJECT/'pynq_identity_ncnn_20261029/board_delivery/vectors_results_v3/all_normalized_features.npz') as ar:gallery=ar['new_gallery'].astype(float)
galleryrows=load(PROJECT/'pynq_identity_ncnn_20261029/input/images.json')['new_gallery']
newpath=PROJECT/'identity_joint_pair_20261030/board_delivery/results/identity_qualification/all_features.npz'
assert sha(newpath)==p['models']['new']['gallery_SHA256']
with np.load(newpath)as a:newgallery=a['normalized'][:30].astype(float)
galleries={'old':gallery,'new':newgallery}
known_features={}
for spec in load(PROJECT/'pynq_mosaic192_joint_20261030/protocol/run_v1.json')['runs']:
 if spec['policy']=='foreground_only':continue
 bg=PROJECT/'pynq_mosaic192_joint_20261030/delivery/results'/spec['run']/'background'
 for job in load(bg/'record.json')['jobs']:
  with np.load(bg/job['vector_file']) as ar:known_features[('old',job['input_tensor_sha256'])]=ar['raw'].tobytes()
rawchecks=ticks=paths=jobs=warmups=pauses=candidate_checks=feature_repeats=0;cases=[];backgrounds=[];job_rows=[]
for run,summary in zip(p['runs'],s['cases']):
 gallery=galleries[run['identity_model']];assert run['identity_model']==summary['identity_model']
 assert summary['run']==run['run'] and summary['case']==run['policy'] and summary['repeat']==run['repeat']
 folder=OUT/'results'/run['run'];rows=load(folder/'timing_rows.json');skips=load(folder/'skipped_slots.json');trace=gz(folder/'counter_trace.json.gz');processed=[r['frame0'] for r in rows]
 t0=summary['clock_start_monotonic_ns'];period=p['period_ns']
 assert sorted([r['slot'] for r in rows]+[r['slot'] for r in skips])==list(range(392))
 for r in rows:
  assert r['frame0']==8915+5*r['slot'] and r['release_monotonic_ns']==t0+period*r['slot']
  assert r['release_monotonic_ns']<=r['started_monotonic_ns']<=r['completed_monotonic_ns']
  assert r['deadline_met']==(r['completed_monotonic_ns']<=r['release_monotonic_ns']+period)
  assert r['release_to_count_ms']==(r['completed_monotonic_ns']-r['release_monotonic_ns'])/1e6 and r['processing_ms']==(r['completed_monotonic_ns']-r['started_monotonic_ns'])/1e6
  assert abs(r['model_ms']+r['after_model_to_count_ms']-r['processing_ms'])<1e-8
  if run['policy'] in ['idle_gate','low_priority_parallel']:
   retained=[f for f in processed if r['frame0']-25<=f<=r['frame0']][-6:]
   assert r['ring_frames']==len(retained)<=6 and r['ring_compressed_bytes']==sum(camera_rows[f]['bytes'] for f in retained)
  else:assert r['ring_frames']==r['ring_compressed_bytes']==r['JPEG_frontend_read_ms']==0
 for r in skips:assert r['skip_observed_monotonic_ns']>=t0+period*(r['slot']+1)
 assert summary['processed_frames']==len(rows) and summary['skipped_slots']==len(skips) and summary['deadline_misses']==sum(not r['deadline_met'] for r in rows)
 assert summary['mean_processing_ms']==np.mean([r['processing_ms'] for r in rows]) and summary['P95_release_to_count_ms']==np.quantile([r['release_to_count_ms'] for r in rows],.95)
 assert summary['processed_per_second_over_offered_duration']==len(rows)/78.4 and summary['ring_peak_compressed_bytes']==max(r['ring_compressed_bytes'] for r in rows)
 with np.load(folder/'actual_raw.npz') as ar:
  assert ar['frame0'].tolist()==processed
  for frame,raw in zip(ar['frame0'],ar['raw']):assert raw.tobytes()==oldraw[frame//5].tobytes();rawchecks+=1
 assert [r['frame0'] for r in trace['observations']]==list(range(0,8915,5))+processed
 for key in ['observations','post_tracker','confirmed_only_events','handoff_events']:assert [r for r in trace[key] if r['frame0']<8915]==[r for r in oldtrace[key] if r['frame0']<8915]
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
   events=[e for e in events if 8912<=e['frame0']<=10873];assert events==summary['periodic_events']
   assert summary['source_down_count']==sum(e['direction']=='A->B' for e in events) and summary['source_up_count']==sum(e['direction']=='B->A' for e in events)
 compact={k:v for k,v in summary.items() if k not in ['periodic_events','cumulative_parent_proc_status']}
 compact.update({'mean_JPEG_frontend_read_ms':float(np.mean([r['JPEG_frontend_read_ms'] for r in rows])),
  'P95_JPEG_frontend_read_ms':float(np.quantile([r['JPEG_frontend_read_ms'] for r in rows],.95)),
  'mean_selector_ms':float(np.mean([r['selector_ms'] for r in rows])),'P95_selector_ms':float(np.quantile([r['selector_ms'] for r in rows],.95)),
  'max_release_to_count_ms':max(r['release_to_count_ms'] for r in rows)})
 cases.append(compact);intervals=load(folder/'worker_pause_intervals.json')
 if run['policy']=='foreground_only':assert intervals==[] and summary['actual_background_jobs']==0;continue
 bg=folder/'background';b=load(bg/'record.json');bt=load(bg/'terminal.json');enqueued=load(folder/'enqueued_identity_jobs.json')
 assert bt['record_sha256']==sha(bg/'record.json') and b['status']==bt['status']=='ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE'
 assert len(b['jobs'])==b['model_forwards']==len(enqueued)==summary['actual_background_jobs'] and b['PNG_compress_level']==0 and len(b['warmups'])==1;warmups+=1
 if run['policy']=='idle_gate':
  assert len(intervals)==len(rows)
  for interval,row in zip(intervals,rows):
   assert interval['slot']==row['slot'] and interval['pause_acknowledged_monotonic_ns']<=row['started_monotonic_ns']<=row['completed_monotonic_ns']<=interval['resume_sent_monotonic_ns'];pauses+=1
 else:assert intervals==[]
 assert b['execution_policy']==run['policy'] and b['actual_nice']==10 and b['actual_CPU_affinity']==[0,1]
 assert b['identity_model']==run['identity_model']and b['encoder_bin_sha256']==p['models'][run['identity_model']]['encoder_bin_sha256']and b['gallery_features_sha256']==p['models'][run['identity_model']]['gallery_SHA256']
 assert all(mask==[0,1]for mask in b['after_warmup_thread_affinities'].values())
 payload_bytes=0
 for job,request in zip(b['jobs'],enqueued):
  assert job['event']==request['event'] and job['source_frame0']==request['source_frame0'] and job['identity_reference_available'] is False and job['selection']==request['selection']
  assert request['event'] in summary['periodic_events'] and request['event_source_frame0']==request['event']['frame0']
  candidate_checks+=verify_selection(request['selection'],processed,byframe)
  chosen=request['selection']['used_candidate'];assert chosen['frame0']==job['source_frame0'] and chosen['xyxy']==request['box_native_xyxy']==job['native_selected_tracker_box']
  assert job['started_monotonic_ns']>=job['enqueued_monotonic_ns']>=job['release_monotonic_ns']
  assert job['queue_wait_ms']==(job['started_monotonic_ns']-job['enqueued_monotonic_ns'])/1e6 and job['enqueue_to_result_ms']==(job['completed_monotonic_ns']-job['enqueued_monotonic_ns'])/1e6
  highres=camera/'highres'/('f'+str(job['source_frame0']).zfill(5)+'.jpg');assert sha(highres)==job['source_JPEG_sha256']==camera_rows[job['source_frame0']]['sha256']
  assert highres.stat().st_size==job['source_JPEG_bytes']
  if run['policy'] in ['idle_gate','low_priority_parallel']:assert job['JPEG_source']=='causal_compressed_ring';payload_bytes+=job['source_JPEG_bytes']
  else:assert job['JPEG_source']=='same_frame_file_read'
  with Image.open(highres) as im:im.load();native=im.convert('RGB')
  x,y,z,w=request['box_native_xyxy'];crop=[max(0,math.floor(x-870)),max(0,math.floor(y)),min(1050,math.ceil(z-870)),min(1440,math.ceil(w))]
  expected=native.crop(crop).transpose(Image.Transpose.ROTATE_270);photo=bg/job['photo_file'];assert sha(photo)==job['photo_sha256'] and job['native_source_crop_xyxy']==crop
  with Image.open(photo) as im:im.load();assert im.convert('RGB').tobytes()==expected.tobytes()
  tensor=body.body_tensor(expected);assert sha(bg/job['vector_file'])==job['vector_sha256']
  with np.load(bg/job['vector_file']) as ar:
   assert tensor.tobytes()==ar['input'].tobytes() and hashlib.sha256(tensor.tobytes()).hexdigest()==job['input_tensor_sha256']
   assert hashlib.sha256(ar['raw'].tobytes()).hexdigest()==job['raw_feature_sha256']
   key=(run['identity_model'],job['input_tensor_sha256'])
   if key in known_features:assert known_features[key]==ar['raw'].tobytes();feature_repeats+=1
   known_features[key]=ar['raw'].tobytes()
   feature=ar['raw'].astype(float)/np.linalg.norm(ar['raw'].astype(float));assert np.max(np.abs(feature-ar['normalized']))<1e-7
   dots=ar['normalized'].astype(float)@gallery.T;scores=np.array([max(dots[i] for i,r in enumerate(galleryrows) if r['identity']==label) for label in p['registered_IDs']])
   assert np.max(np.abs(scores-ar['scores']))<1e-12
   winner=int(np.argmax(scores));assert p['registered_IDs'][winner]==job['predicted_id'] and abs(float(scores[winner])-job['similarity'])<1e-12 and bool(scores[winner]>=p['fixed_identity_threshold'])==job['accepted']
  assert job['identity_model']==run['identity_model']and job['secondary_Cows_threshold_accepted']==(job['similarity']>=p['secondary_Cows_threshold'])and all(mask==[0,1]for mask in job['thread_affinities_after_job'].values())
  jobs+=1;job_rows.append({'run':run['run'],'policy':run['policy'],'repeat':run['repeat'],'identity_model':run['identity_model'],'vector_file':str((bg/job['vector_file']).resolve()),'input_tensor_sha256':job['input_tensor_sha256'],'queue_wait_ms':job['queue_wait_ms'],'enqueue_to_result_ms':job['enqueue_to_result_ms'],'network_ms':job['actual_identity_network_ms'],'secondary_Cows_threshold_accepted':job['secondary_Cows_threshold_accepted'],'event':job['event'],'source_frame0':job['source_frame0'],'selected_age_frames':job['event_source_frame0']-job['source_frame0'],'candidate_count':len(job['selection']['candidates']),'predicted_id':job['predicted_id'],'similarity':job['similarity'],'accepted':job['accepted'],'photo_file':str(photo.resolve()),'photo_sha256':sha(photo),'used_geometry':chosen})
 assert payload_bytes==summary['enqueued_JPEG_payload_bytes_total']
 backgrounds.append({'run':run['run'],'policy':run['policy'],'repeat':run['repeat'],'identity_model':run['identity_model'],'actual_jobs':len(b['jobs']),'accepted_provisional_predictions':sum(j['accepted'] for j in b['jobs']),
  'max_queue_wait_ms':max((j['queue_wait_ms'] for j in b['jobs']),default=0.),'max_enqueue_to_result_ms':max((j['enqueue_to_result_ms'] for j in b['jobs']),default=0.),
  'mean_network_elapsed_ms':float(np.mean([j['actual_identity_network_ms'] for j in b['jobs']])) if b['jobs'] else None,
  'saved_photo_bytes':sum((bg/j['photo_file']).stat().st_size for j in b['jobs']),'chosen_older_frame_jobs':sum(j['source_frame0']<j['event_source_frame0'] for j in b['jobs'])})
assert len(cases)==4 and rawchecks==s['actual_O8_forwards'] and ticks==4*1783+rawchecks and paths==8 and warmups==4
assert rawchecks<=p['maximum_timed_O8_forwards'] and jobs<=p['maximum_formal_identity_queries']
assert rawchecks+16+jobs+warmups<=p['maximum_total_board_image_forwards']
assert all(case['actual_background_jobs']<=p['maximum_identity_jobs_per_case']for case in cases)
result={'status':'FOUR_PARENT_ONLY_ACTUAL_COUNT_TRIGGER_RUNS_RAW_EVENTS_CAUSAL_PHOTOS_INPUTS_AND_MODEL_MATCHED_SCORES_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'actual_O8_timed_forwards':rawchecks,'actual_O8_qualification_forwards':8,'actual_O8_warmups':8,'counter_observation_ticks_with_history':ticks,'counter_paths':paths,'cases':cases,
 'actual_background_identity_jobs':jobs,'identity_warmups':warmups,'all_new_actual_board_forwards':rawchecks+16+jobs+warmups,'backgrounds':backgrounds,'pause_windows_verified':pauses,'candidate_observations_separately_recomputed':candidate_checks,
 'same_tensor_actual_ARM_features_byte_exact_checks':feature_repeats,'all_runtime_photos_inputs_features_scores_recomputed':True,'all_selected_JPEGs_match_frozen_source':True,
 'ring_payload_not_total_process_or_queue_memory':True,'async_queue_copy_after_enqueue_not_claimed_inside_count_timer':True,'both_networks_run_on_same_PYNQ':True,'input_is_public_replay_RFID_is_simulated':True,
 'permanent_identity_accuracy_newly_proven':False,'repeats_are_same_source_not_independent_sessions':True,'parent_and_four_background_workers_terminal_absent':True,'new_training_updates':0,'new_independent_test':False,'whole_goal_complete':False}
for name,obj in [('independent_verification.json',result),('actual_job_rows.json',job_rows)]:
 f=ROOT/'results'/name;assert not f.exists();f.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['cases','backgrounds']}))
