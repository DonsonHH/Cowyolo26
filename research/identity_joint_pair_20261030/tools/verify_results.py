"""Audit saved real outputs, same photos and independent event/state arithmetic."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import gzip,hashlib,importlib.util,json,math,sys
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;BOARD=ROOT/'board_delivery'
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def gz(p):return json.loads(gzip.decompress(p.read_bytes()))
def module(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n')

scanner=module('pair_event_scanner',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py')
body=module('pair_frozen_body',PROJECT/'identity_domain_ncnn_20261030/tools/frozen_body_tensor.py')
plan=load(BOARD/'run_protocol.json');assert sha(BOARD/'run_protocol.json')==sha(ROOT/'protocol/run_v1.json')
state=load(BOARD/'results/record.json');done=load(BOARD/'results/terminal.json');final=load(BOARD/'final_state.json')
assert state['status']==done['status']=='ALL4_OLD_NEW_NEW_OLD_IDENTITY_FIXED10_O8_ARM_REPEATS_COMPLETE'
assert done['record_sha256']==sha(BOARD/'results/record.json')and done['close_error']is None
assert state['qualification_forwards']==state['warmup_forwards']==8 and state['hardware_status']['error']=='0x0'
assert final['runtime_hashes_match']and final['shared_lock_available']and all(final['local_services'].values())
assert state['parent_affinity_restored_before_exit']==[0,1]and final['PL_bit_sha256']==plan['O8_bit_sha256']
qroot=BOARD/'results/identity_qualification';qual=load(qroot/'record.json')
assert qual['status']=='NEW_ENCODER40_GALLERY_AND_FIXED_PHOTO_QUALIFICATION_PASS'and qual['measured_forwards']==40 and qual['warmup_forwards']==1
with np.load(qroot/'all_features.npz')as a:qv={key:a[key].copy()for key in a.files}
with np.load(ROOT/'reference_delivery/results/cpu_reference/all_features.npz')as a:cpu={key:a[key].copy()for key in a.files}
with np.load(ROOT/'input/input40.npz')as a:fixed_inputs=a['input'].copy()
for i,(row,actual)in enumerate(zip(plan['identity_reference_images'],qual['rows'])):
 image=Path(row['local_image']);assert sha(image)==row['image_sha256']
 with Image.open(image)as source:x=body.body_tensor(source)
 digest=hashlib.sha256(x.tobytes()).hexdigest();assert x.tobytes()==fixed_inputs[i].tobytes()and digest==actual['input_tensor_sha256']==row['input_tensor_sha256']
 assert hashlib.sha256(qv['raw'][i].tobytes()).hexdigest()==actual['raw_sha256']
 normalized=qv['raw'][i].astype(float)/np.linalg.norm(qv['raw'][i].astype(float));assert np.max(np.abs(normalized-qv['normalized'][i]))<1e-7
 a=float(np.max(np.abs(qv['normalized'][i]-cpu['Torch_normalized'][i])));b=float(np.max(np.abs(qv['normalized'][i]-cpu['NCNN_normalized'][i])))
 assert a==actual['normalized_Torch_error']and b==actual['normalized_NCNN_error']and max(a,b)<1e-4
 assert abs(1-float(qv['normalized'][i].astype(float)@cpu['Torch_normalized'][i].astype(float))-actual['one_minus_dot'])<2e-15
prior_bg=PROJECT/'backend_service_20261030/delivery/results/r1_idle_gate/background';prior_jobs=load(prior_bg/'record.json')['jobs']
with np.load(PROJECT/'pynq_identity_ncnn_20261029/board_delivery/vectors_results_v3/all_normalized_features.npz')as a:oldgallery=a['new_gallery'].astype(float)
newgallery=qv['normalized'][:30].astype(float);grows=plan['identity_reference_images'][:30];labels=plan['registered_IDs']
expected=load(qroot/'expected_queries.json');assert len(expected)==10
for i,row in enumerate(expected):
 values={label:max(float(np.dot(qv['normalized'][30+i].astype(float),newgallery[j]))for j,r in enumerate(grows)if r['identity']==label)for label in labels}
 winner=sorted(labels,key=lambda x:(-values[x],x))[0];assert row['predicted_id']==winner and abs(row['similarity']-values[winner])<1e-12
 assert row['accepted']==(values[winner]>=plan['fixed_identity_threshold'])
source=PROJECT/'pynq_mosaic192_eval_20261030/board_delivery/results/original';oldraw=np.load(source/'all_raw.npy',mmap_mode='r');oldtrace=gz(source/'stride5_counter_trace.json.gz')
camera=PROJECT/'pynq_periodic_joint_20261030/camera_delivery/highres';rawcount=ticks=paths=photos=0;actual_jobs=[];cases=[]
for spec,case in zip(plan['runs'],state['cases']):
 folder=BOARD/'results'/spec['run'];assert case['identity_model']==spec['identity_model'];model=spec['identity_model'];gallery=oldgallery if model=='old'else newgallery
 rows=load(folder/'timing_rows.json');skips=load(folder/'skipped_slots.json');trace=gz(folder/'counter_trace.json.gz');epoch=case['clock_start_monotonic_ns']
 assert sorted([r['slot']for r in rows]+[r['slot']for r in skips])==list(range(392))and len(rows)==case['processed_frames']and len(skips)==case['skipped_slots']
 for row in rows:
  assert row['frame0']==8915+5*row['slot']and row['release_monotonic_ns']==epoch+row['slot']*200000000
  assert row['release_monotonic_ns']<=row['started_monotonic_ns']<=row['completed_monotonic_ns']
  assert row['release_to_count_ms']==(row['completed_monotonic_ns']-row['release_monotonic_ns'])/1e6
  assert row['processing_ms']==(row['completed_monotonic_ns']-row['started_monotonic_ns'])/1e6 and 0<=row['model_ms']<=row['processing_ms']
  assert row['deadline_met']==(row['completed_monotonic_ns']<=row['release_monotonic_ns']+200000000)
  a,b=row['worker_CPU_before'],row['worker_CPU_after'];assert a['PID']==b['PID']and a['starttime_ticks']==b['starttime_ticks']and a['nice']==b['nice']==10
  assert a['clock_ticks_per_second']==b['clock_ticks_per_second']==100
  assert a['snapshot_finished_monotonic_ns']<=row['started_monotonic_ns']and b['snapshot_finished_monotonic_ns']<=row['completed_monotonic_ns']
  assert row['worker_CPU_tick_delta']==b['total_CPU_ticks']-a['total_CPU_ticks']>=0
 for row in skips:assert row['skip_observed_monotonic_ns']>=epoch+(row['slot']+1)*200000000
 assert sum(not row['deadline_met']for row in rows)==case['deadline_misses']and len(rows)/78.4==case['processed_per_second_over_offered_duration']
 assert float(np.mean([r['processing_ms']for r in rows]))==case['mean_processing_ms']and float(np.quantile([r['release_to_count_ms']for r in rows],.95))==case['P95_release_to_count_ms']
 with np.load(folder/'actual_raw.npz')as a:
  assert a['frame0'].tolist()==[r['frame0']for r in rows]
  for frame,raw in zip(a['frame0'],a['raw']):assert raw.tobytes()==oldraw[int(frame)//5].tobytes();rawcount+=1
 assert [r['frame0']for r in trace['observations']]==list(range(0,8915,5))+[r['frame0']for r in rows]
 for key in trace:assert [r for r in trace[key]if r['frame0']<8915]==[r for r in oldtrace[key]if r['frame0']<8915]
 post=defaultdict(list)
 for row in trace['post_tracker']:post[row['frame0']].append(row)
 for obs in trace['observations']:
  positions={};ids=set()
  for row in post[obs['frame0']]:
   tid=row['track_id']
   if tid is None:continue
   ids.add(tid);x1,y1,x2,y2=row['xyxy']
   if .34<(x1+x2)/(2*2560)<.75:positions[str(tid)]=(y1+y2)/(2*1440)
  assert obs['confirmed_positions']==positions and obs['confirmed_IDs']==sorted(ids)
 ticks+=len(trace['observations'])
 for key,handoff in[('confirmed_only_events',False),('handoff_events',True)]:
  events,_=scanner.batch_events(trace['observations'],handoff);assert events==trace[key];paths+=1
  if handoff:
   scoped=[e for e in events if 8912<=e['frame0']<=10873];assert scoped==case['periodic_events']and sum(e['direction']=='A->B'for e in scoped)==case['source_down_count']and sum(e['direction']=='B->A'for e in scoped)==case['source_up_count']
 publications=load(folder/'fixed_job_publication.json')['records'];worker=load(folder/'background/record.json');terminal=load(folder/'background/terminal.json')
 assert worker['status']==terminal['status']=='ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE'and terminal['record_sha256']==sha(folder/'background/record.json')
 assert len(publications)==len(worker['jobs'])==worker['model_forwards']==10 and len(worker['warmups'])==1
 assert worker['identity_model']==model and worker['encoder_bin_sha256']==plan['models'][model]['encoder_bin_sha256']
 assert worker['actual_nice']==10 and worker['actual_CPU_affinity']==[0,1]and worker['NCNN_threads']==1 and all(mask==[0,1]for mask in worker['after_warmup_thread_affinities'].values())
 for i,(pub,job,fixed,prior)in enumerate(zip(publications,worker['jobs'],plan['fixed_jobs'],prior_jobs)):
  assert pub['fixed_job_index']==job['fixed_job_index']==i and job['identity_model']==model
  assert pub['requested_monotonic_ns']==epoch+fixed['requested_enqueue_offset_ns']==job['requested_enqueue_monotonic_ns']==job['release_monotonic_ns']
  assert job['enqueued_monotonic_ns']==pub['enqueue_started_monotonic_ns']>=pub['requested_monotonic_ns']and pub['publisher_CPU_affinity']==[0,1]
  assert pub['publisher_lateness_ms']==(pub['enqueue_started_monotonic_ns']-pub['requested_monotonic_ns'])/1e6
  assert all(mask==[0,1]for mask in job['thread_affinities_after_job'].values())and job['source_frame0']==fixed['source_frame0']==prior['source_frame0']
  assert job['event']==fixed['event']and job['selection']==fixed['selection']and job['identity_reference_available']is False and job['JPEG_source']=='same_frame_file_read'
  assert job['queue_wait_ms']==(job['started_monotonic_ns']-job['enqueued_monotonic_ns'])/1e6 and job['enqueue_to_result_ms']==(job['completed_monotonic_ns']-job['enqueued_monotonic_ns'])/1e6
  jpeg=camera/('f'+str(job['source_frame0']).zfill(5)+'.jpg');assert sha(jpeg)==job['source_JPEG_sha256']==fixed['source_JPEG_sha256']
  with Image.open(jpeg)as im:native=im.convert('RGB')
  left,top,right,bottom=fixed['box_native_xyxy'];crop=[max(0,math.floor(left-870)),max(0,math.floor(top)),min(1050,math.ceil(right-870)),min(1440,math.ceil(bottom))]
  photo=native.crop(crop).transpose(Image.Transpose.ROTATE_270);saved=folder/'background'/job['photo_file'];assert sha(saved)==job['photo_sha256']==prior['photo_sha256']
  with Image.open(saved)as im:assert im.convert('RGB').tobytes()==photo.tobytes()
  x=body.body_tensor(photo);vector=folder/'background'/job['vector_file'];assert sha(vector)==job['vector_sha256']
  with np.load(vector)as a:
   assert x.tobytes()==a['input'].tobytes()==fixed_inputs[30+i].tobytes()and hashlib.sha256(a['raw'].tobytes()).hexdigest()==job['raw_feature_sha256']
   raw=a['raw'].astype(float);assert np.max(np.abs(raw/np.linalg.norm(raw)-a['normalized']))<1e-7
   if model=='old':
    with np.load(prior_bg/prior['vector_file'])as reference:
     for key in['input','raw','normalized','scores']:assert a[key].tobytes()==reference[key].tobytes()
   else:
    assert a['raw'].tobytes()==qv['raw'][30+i].tobytes()and a['normalized'].tobytes()==qv['normalized'][30+i].tobytes()
   values={label:max(float(np.dot(a['normalized'].astype(float),gallery[j]))for j,r in enumerate(grows)if r['identity']==label)for label in labels}
   scores=np.array([values[label]for label in labels]);assert np.max(np.abs(scores-a['scores']))<1e-12
   winner=sorted(labels,key=lambda label:(-values[label],label))[0];assert winner==job['predicted_id']and abs(values[winner]-job['similarity'])<1e-12
   assert job['accepted']==(values[winner]>=plan['fixed_identity_threshold'])and job['secondary_Cows_threshold_accepted']==(values[winner]>=plan['secondary_Cows_threshold'])
  photos+=1
  actual_jobs.append({'run':spec['run'],'repeat':spec['repeat'],'identity_model':model,'fixed_job_index':i,'source_frame0':job['source_frame0'],'photo_file':str(saved.resolve()),'photo_sha256':sha(saved),'predicted_id':job['predicted_id'],'similarity':job['similarity'],'accepted':job['accepted'],'secondary_Cows_threshold_accepted':job['secondary_Cows_threshold_accepted'],'queue_ms':job['queue_wait_ms'],'enqueue_to_result_ms':job['enqueue_to_result_ms'],'network_ms':job['actual_identity_network_ms']})
 cases.append({**{k:v for k,v in case.items()if k not in['periodic_events','foreground_proc_status']},'mean_model_ms':float(np.mean([r['model_ms']for r in rows])),'maximum_identity_result_ms':max(j['enqueue_to_result_ms']for j in worker['jobs']),'maximum_identity_queue_ms':max(j['queue_wait_ms']for j in worker['jobs']),'accepted_predictions':sum(j['accepted']for j in worker['jobs']),'secondary_Cows_threshold_accepted':sum(j['secondary_Cows_threshold_accepted']for j in worker['jobs'])})
assert rawcount==state['actual_O8_forwards']and len(cases)==4 and photos==40 and paths==8 and ticks==4*1783+rawcount
assert len({j['photo_sha256']for j in actual_jobs})==10
pairs=[]
for repeat in[1,2]:
 for i in range(10):
  a=next(j for j in actual_jobs if j['repeat']==repeat and j['identity_model']=='old'and j['fixed_job_index']==i);b=next(j for j in actual_jobs if j['repeat']==repeat and j['identity_model']=='new'and j['fixed_job_index']==i);assert a['photo_sha256']==b['photo_sha256']
  pairs.append({'repeat':repeat,'fixed_job_index':i,'photo_sha256':a['photo_sha256'],'new_minus_old_result_ms':b['enqueue_to_result_ms']-a['enqueue_to_result_ms'],'new_minus_old_queue_ms':b['queue_ms']-a['queue_ms'],'old_candidate':a['predicted_id'],'new_candidate':b['predicted_id'],'old_accepted':a['accepted'],'new_accepted':b['accepted']})
for model in['old','new']:
 a=[j for j in actual_jobs if j['identity_model']==model and j['repeat']==1];b=[j for j in actual_jobs if j['identity_model']==model and j['repeat']==2]
 for x,y in zip(a,b):assert all(x[k]==y[k]for k in['fixed_job_index','photo_sha256','predicted_id','similarity','accepted','secondary_Cows_threshold_accepted'])
result={'status':'ALL4_IDENTITY_PAIR_RUNS_REAL_RAW_TIMING_COUNTER_OBSERVATIONS40_PHOTOS_AND_MODEL_MATCHED_GALLERIES_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),'actual_timed_O8_forwards':rawcount,'actual_O8_qualification_forwards':8,'actual_O8_warmups':8,'actual_ARM_gallery_qualification_images':40,'actual_ARM_gallery_qualification_warmups':1,'actual_ARM_timed_queries':40,'actual_ARM_timed_warmups':4,'actual_ARM_total_forwards':85,'all_new_actual_board_forwards':rawcount+16+85,'new_Torch_reference_forwards':40,'new_NCNN_CPU_reference_forwards':40,'counter_observation_ticks':ticks,'independently_recomputed_counter_paths':paths,'photo_input_feature_score_jobs_verified':40,'unique_fixed_photos':10,'same_photo_new_old_pairs':20,'new_qualified_gallery_and_query_features_verified':40,'case_models':[c['identity_model']for c in cases],'cases':cases,'tracker_scope':'Recorded post_tracker boxes to positions and full event state machines independently checked; association optimization itself is not rerun locally.','permanent_event_ID_accuracy_known':False,'new_training_updates':0,'future20_ID_pixels_opened':False,'new_independent_test':False,'default_model_or_policy_changed':False,'whole_goal_complete':False}
for name,value in[('independent_verification.json',result),('actual_job_rows.json',actual_jobs),('paired_jobs.json',pairs)]:save(ROOT/'results'/name,value)
print(json.dumps({k:v for k,v in result.items()if k!='cases'}),flush=True)
