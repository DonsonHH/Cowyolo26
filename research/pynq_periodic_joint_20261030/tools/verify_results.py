from pathlib import Path
from datetime import datetime,timezone
from PIL import Image,ImageOps
import json,gzip,hashlib,tarfile,importlib.util,sys,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def gz(p):return json.loads(gzip.decompress(p.read_bytes()))
m=load(ROOT/'evidence/transfer.json');archive=ROOT/'results_delivery.tar.gz';assert sha(archive)==m['sha256'] and archive.stat().st_size==m['bytes']
OUT=ROOT/'delivery';OUT.mkdir(exist_ok=True)
with tarfile.open(archive) as tar:
 members=tar.getmembers();assert len(members)==m['members']
 for member in members:
  assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
  p=(OUT/member.name).resolve();assert p.is_relative_to(OUT.resolve())
  contents=tar.extractfile(member).read()
  if p.exists():assert p.read_bytes()==contents
  else:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(contents)
manifest=load(OUT/'result_manifest.json');assert len(manifest)==m['manifest_files']
for row in manifest:
 p=OUT/row['file'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
for relative in ['board_periodic_v2.py','background_worker_v2.py']:assert sha(OUT/relative)==sha(ROOT/'tools'/relative)
assert sha(OUT/'protocol_template_v2.json')==sha(ROOT/'protocol/run_template_v2.json')
p=load(OUT/'protocol.json');s=load(OUT/'results/record.json');terminal=load(OUT/'results/terminal.json')
assert s['status']==terminal['status']=='BOTH392_SLOT_PERIODIC_FRONTEND_CASES_AND_ACTUAL_TRIGGERED_BACKGROUND_COMPLETE'
assert s['protocol_sha256']==sha(OUT/'protocol.json') and terminal['record_sha256']==sha(OUT/'results/record.json')
assert s['actual_O8_forwards']==781 and s['qualification_forwards']==8 and s['warmup_forwards']==4
assert terminal['close_error'] is None and s['hardware_status']['error']=='0x0' and s['PL_after_sha256']==p['O8_bit_sha256']
assert len(s['BGR_actual_vector_gate'])==8 and all(row['BGR_input_to_complete_O8_raw_byte_exact'] for row in s['BGR_actual_vector_gate'])
spec=importlib.util.spec_from_file_location('independent_periodic_event_scanner',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py')
scanner=importlib.util.module_from_spec(spec);sys.modules[spec.name]=scanner;spec.loader.exec_module(scanner)
spec=importlib.util.spec_from_file_location('independent_verified_body_input',PROJECT/'pynq_identity_ncnn_20261029/tools/ncnn_encoder_v3.py')
body=importlib.util.module_from_spec(spec);spec.loader.exec_module(body)
previous=PROJECT/'pynq_rot192_eval_20261029/board_delivery/results_v2/original';oldraw=np.load(previous/'all_raw.npy',mmap_mode='r');oldtrace=gz(previous/'stride5_counter_trace.json.gz')
cases=[];total_raw=total_ticks=paths=0
for case in p['cases']:
 folder=OUT/'results'/case;rows=load(folder/'timing_rows.json');skips=load(folder/'skipped_slots.json');trace=gz(folder/'counter_trace.json.gz')
 summary=next(r for r in s['cases'] if r['case']==case);t0=summary['clock_start_monotonic_ns'];period=p['period_ns']
 assert sorted([r['slot'] for r in rows]+[r['slot'] for r in skips])==list(range(392))
 assert len({r['slot'] for r in rows})==len(rows) and len(rows)==summary['processed_frames'] and len(skips)==summary['skipped_slots']
 for row in rows:
  assert row['frame0']==8915+5*row['slot'] and row['release_monotonic_ns']==t0+period*row['slot']
  assert row['release_monotonic_ns']<=row['started_monotonic_ns']<=row['completed_monotonic_ns']
  assert row['deadline_met']==(row['completed_monotonic_ns']<=row['release_monotonic_ns']+period)
  assert abs(row['processing_ms']-(row['completed_monotonic_ns']-row['started_monotonic_ns'])/1e6)<1e-9
  assert abs(row['release_to_count_ms']-(row['completed_monotonic_ns']-row['release_monotonic_ns'])/1e6)<1e-9
  assert abs(row['model_ms']+row['after_model_to_count_ms']-row['processing_ms'])<1e-8
 for row in skips:
  assert row['source_frame0']==8915+5*row['slot'] and row['release_monotonic_ns']==t0+period*row['slot']
  assert row['skip_observed_monotonic_ns']>=row['release_monotonic_ns']+period
 assert sum(not r['deadline_met'] for r in rows)==summary['deadline_misses']
 assert np.mean([r['processing_ms'] for r in rows])==summary['mean_processing_ms']
 assert np.quantile([r['release_to_count_ms'] for r in rows],.95)==summary['P95_release_to_count_ms']
 assert summary['period_end_monotonic_ns']-t0==392*period and len(rows)/78.4==summary['processed_per_second_over_offered_duration']
 with np.load(folder/'actual_raw.npz') as a:
  assert a['frame0'].tolist()==[r['frame0'] for r in rows]
  assert a['raw'].shape==(len(rows),300,6) and np.isfinite(a['raw']).all()
  for frame,raw in zip(a['frame0'],a['raw']):assert raw.tobytes()==oldraw[frame//5].tobytes();total_raw+=1
 assert [r['frame0'] for r in trace['observations']]==list(range(0,8915,5))+[r['frame0'] for r in rows]
 for key in ['observations','post_tracker','confirmed_only_events','handoff_events']:
  assert [r for r in trace[key] if r['frame0']<8915]==[r for r in oldtrace[key] if r['frame0']<8915]
 total_ticks+=len(trace['observations'])
 for key,admit in [('confirmed_only_events',False),('handoff_events',True)]:
  events,accepted=scanner.batch_events(trace['observations'],admit);assert events==trace[key];paths+=1
  if admit:
   selected=[e for e in events if 8912<=e['frame0']<=10873]
   assert selected==summary['periodic_events'] and summary['source_down_count']==sum(e['direction']=='A->B' for e in selected)
 report={k:summary[k] for k in ['case','processed_frames','skipped_slots','deadline_misses','source_down_count','source_up_count','processed_per_second_over_offered_duration','mean_processing_ms','P95_release_to_count_ms','actual_background_jobs']}
 report['mean_release_to_start_ms']=float(np.mean([(r['started_monotonic_ns']-r['release_monotonic_ns'])/1e6 for r in rows]))
 report['maximum_release_to_count_ms']=max(r['release_to_count_ms'] for r in rows);report['processed_model_raw_byte_exact']=len(rows)
 cases.append(report)
bg=OUT/'results/foreground_with_identity/background';backend=load(bg/'record.json');bt=load(bg/'terminal.json')
assert backend['status']==bt['status']=='ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE' and bt['record_sha256']==sha(bg/'record.json')
jobs=load(OUT/'results/foreground_with_identity/enqueued_identity_jobs.json');assert len(jobs)==backend['model_forwards']==len(backend['jobs'])==11 and len(backend['warmups'])==1
identity=PROJECT/'pynq_identity_ncnn_20261029/board_delivery'
with np.load(identity/'vectors_results_v3/all_normalized_features.npz') as ar:gallery=ar['new_gallery'].copy()
galleryrows=load(PROJECT/'pynq_identity_ncnn_20261029/input/images.json')['new_gallery'];photo_checks=[]
for actual,job in zip(backend['jobs'],jobs):
 assert actual['event']==job['event'] and actual['source_frame0']==job['source_frame0']
 source=ROOT/'camera_delivery/highres'/('f'+str(actual['source_frame0']).zfill(5)+'.jpg')
 with Image.open(source) as im:im.load();native=im.convert('RGB')
 x1,y1,x2,y2=job['box_native_xyxy'];crop=[max(0,math.floor(x1-870)),max(0,math.floor(y1)),min(1050,math.ceil(x2-870)),min(1440,math.ceil(y2))]
 assert crop==actual['native_source_crop_xyxy'];expected=native.crop(crop).transpose(Image.Transpose.ROTATE_270)
 file=bg/actual['photo_file'];assert sha(file)==actual['photo_sha256']
 with Image.open(file) as im:im.load();assert np.array_equal(np.asarray(im.convert('RGB')),np.asarray(expected));assert list(im.size)==actual['photo_size_WH']
 tensor=body.body_tensor(expected);assert hashlib.sha256(tensor.tobytes()).hexdigest()==actual['input_tensor_sha256']
 with np.load(bg/actual['vector_file']) as a:
  assert a['input'].tobytes()==tensor.tobytes() and hashlib.sha256(a['raw'].tobytes()).hexdigest()==actual['raw_feature_sha256']
  z=a['raw'].astype(float)/np.linalg.norm(a['raw'].astype(float));assert np.max(np.abs(z-a['normalized']))<1e-7
  dots=a['normalized'].astype(float)@gallery.astype(float).T
  scores=[max(dots[i] for i,row in enumerate(galleryrows) if row['identity']==label) for label in p['registered_IDs']]
  assert np.max(np.abs(np.asarray(scores)-a['scores']))<1e-12
  index=int(np.argmax(scores));assert actual['predicted_id']==p['registered_IDs'][index] and abs(actual['similarity']-scores[index])<1e-12
  assert actual['accepted']==(scores[index]>=p['fixed_identity_threshold'])
 assert actual['started_monotonic_ns']>=actual['enqueued_monotonic_ns'] and actual['completed_monotonic_ns']>=actual['inference_finished_monotonic_ns']
 assert actual['queue_wait_ms']==(actual['started_monotonic_ns']-actual['enqueued_monotonic_ns'])/1e6
 photo_checks.append({'frame0':actual['source_frame0'],'photo_file':str(file.resolve()),'photo_pixels_exact_to_same_frame_runtime_box':True,
  'runtime_body_tensor_bytes_reconstructed_exact':True,'predicted_id':actual['predicted_id'],'similarity':actual['similarity'],'accepted':actual['accepted'],'has_identity_GT':False})
assert total_raw==781 and total_ticks==4347 and paths==4
result={'status':'BOTH_PERIODIC_CASES781_ACTUAL_O8_FRAMES4_EVENT_PATHS_AND11_ACTUAL_HIGHRES_IDENTITY_JOBS_INDEPENDENTLY_VERIFIED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'actual_O8_timed_frames':781,'O8_BGR_qualification_forwards':8,'O8_warmups':4,
 'offered_slots_each':392,'period_ns':period,'cases':cases,'independent_counter_paths':paths,'counter_observation_ticks_including_history':total_ticks,
 'actual_background_identity_jobs':11,'identity_warmups':1,'runtime_photo_pixels_and_input_tensor_checks':11,
 'background_accepted_predictions':sum(r['accepted'] for r in backend['jobs']),'background_identity_accuracy_proven':False,
 'maximum_background_queue_wait_ms':max(r['queue_wait_ms'] for r in backend['jobs']),
 'maximum_background_enqueue_to_result_ms':max(r['enqueue_to_result_ms'] for r in backend['jobs']),
 'photo_checks':photo_checks,'same_PYNQ_actual_detection_tracking_photo_preprocess_and_identity_executed':True,
 'stable_joint5Hz_proven':False,'real_camera_and_RFID_devices_used':False,'whole_goal_complete':False,
 'archive_sha256':sha(archive),'archive_members':len(members),'manifest_files':len(manifest)}
file=ROOT/'results/independent_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='photo_checks'}))
