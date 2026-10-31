"""Audit recovered metadata without claiming recovery of absent photos or arrays."""
from pathlib import Path,PurePosixPath
from collections import defaultdict
from datetime import datetime,timezone
import json,gzip,hashlib,tarfile,importlib.util,sys,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def gz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
meta=load(ROOT/'evidence/metadata_UART_transfer.json');a=ROOT/'metadata_only_uart.tar.gz'
assert meta['status']=='UART_METADATA_ARCHIVE_COMPLETE_HASH_VERIFIED' and a.stat().st_size==meta['bytes'] and sha(a)==meta['sha256']
out=ROOT/'metadata_recovery';out.mkdir(exist_ok=False)
with tarfile.open(a) as tar:
 members=tar.getmembers();assert len(members)==95
 for item in members:
  path=PurePosixPath(item.name);assert item.isfile() and not path.is_absolute() and '..' not in path.parts
  f=out.joinpath(*path.parts).resolve();assert f.is_relative_to(out.resolve()) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(item).read())
original_manifest=load(out/'result_manifest.json');present=[];missing=[]
for row in original_manifest:
 f=out/row['file']
 if f.is_file():assert sha(f)==row['sha256'] and f.stat().st_size==row['bytes'];present.append(row['file'])
 else:missing.append(row)
p=load(out/'run_protocol.json');state=load(out/'results/record.json');terminal=load(out/'results/terminal.json')
assert sha(out/'run_protocol.json')==sha(ROOT/'protocol/run_v1.json')==state['protocol_sha256']
assert sha(out/'results/record.json')==terminal['record_sha256']==sha(ROOT/'evidence/terminal_experiment_record.json')
assert state['status']==terminal['status']=='ALL_FOUR392_SLOT_IDLE_LOW_PRIORITY_BACKEND_SAME_BOARD_REPEATS_COMPLETE'
assert state['actual_O8_forwards']==1466 and state['qualification_forwards']==state['warmup_forwards']==8
for row in p['payload_files']:
 f=out/row['file']
 if f.exists():assert sha(f)==row['sha256']==sha(ROOT/'tools'/row['file'])
spec=importlib.util.spec_from_file_location('recovered_independent_counter',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py');scanner=importlib.util.module_from_spec(spec);sys.modules[spec.name]=scanner;spec.loader.exec_module(scanner)
sys.path.insert(0,str(ROOT/'tools'));from independent_geometry import verify_selection
oldtrace=gz(PROJECT/'pynq_mosaic192_eval_20261030/board_delivery/results/original/stride5_counter_trace.json.gz')
camera={r['frame0']:r for r in load(PROJECT/'pynq_periodic_joint_20261030/camera_delivery/manifest.json')}
ticks=paths=source_records=jobs=candidates=CPUwindows=0;cases=[]
for run,case in zip(p['runs'],state['cases']):
 folder=out/'results'/run['run'];rows=load(folder/'timing_rows.json');skips=load(folder/'skipped_slots.json');trace=gz(folder/'counter_trace.json.gz');processed=[r['frame0'] for r in rows]
 assert case['run']==run['run'] and sorted([r['slot'] for r in rows]+[r['slot'] for r in skips])==list(range(392))
 for key in ['observations','post_tracker','confirmed_only_events','handoff_events']:assert [r for r in trace[key] if r['frame0']<8915]==[r for r in oldtrace[key] if r['frame0']<8915]
 assert [r['frame0'] for r in trace['observations']]==list(range(0,8915,5))+processed
 post=defaultdict(list)
 for row in trace['post_tracker']:post[row['frame0']].append(row)
 for row in trace['observations']:
  positions={};ids=set()
  for r in post[row['frame0']]:
   tid=r['track_id']
   if tid is None:continue
   ids.add(tid);x,y,z,w=r['xyxy']
   if .34<(x+z)/5120<.75:positions[str(tid)]=(y+w)/2880
  assert row['confirmed_positions']==positions and row['confirmed_IDs']==sorted(ids)
 for kind,admit in [('confirmed_only_events',False),('handoff_events',True)]:
  events,_=scanner.batch_events(trace['observations'],admit);assert events==trace[kind];paths+=1
  if admit:assert [e for e in events if 8912<=e['frame0']<=10873]==case['periodic_events']
 ticks+=len(trace['observations'])
 assert case['processed_frames']==len(rows) and case['skipped_slots']==len(skips) and case['deadline_misses']==sum(not r['deadline_met'] for r in rows)
 CPUpositive=CPUticks=0;packets=load(folder/'input_packets.json');producer=load(folder/'producer_record.json');pauses=load(folder/'worker_pause_intervals.json')
 assert producer['status']=='JPEG_PRODUCER_COMPLETE' and not producer['thread_alive'] and producer['pinned_at_end'] is None and len(producer['records'])==392
 for slot,row in enumerate(producer['records']):
  assert row['frame0']==8915+5*slot and row['release_monotonic_ns']==case['clock_start_monotonic_ns']+slot*p['period_ns']
  assert row['release_monotonic_ns']<=row['read_started_monotonic_ns']<=row['read_finished_monotonic_ns']<=row['verified_monotonic_ns']<=row['published_monotonic_ns']
  assert row['JPEG_bytes']==camera[row['frame0']]['bytes'] and row['JPEG_sha256']==camera[row['frame0']]['sha256'];source_records+=1
 assert len(packets)==len(rows)
 for row,packet in zip(rows,packets):
  assert row['release_monotonic_ns']==case['clock_start_monotonic_ns']+row['slot']*p['period_ns'] and row['frame0']==8915+5*row['slot']
  assert row['deadline_met']==(row['completed_monotonic_ns']<=row['release_monotonic_ns']+p['period_ns'])
  assert row['processing_ms']==(row['completed_monotonic_ns']-row['started_monotonic_ns'])/1e6 and row['release_to_count_ms']==(row['completed_monotonic_ns']-row['release_monotonic_ns'])/1e6
  assert row['frame0']==packet['frame0'] and row['JPEG_frontend_read_ms']==(packet['foreground_received_monotonic_ns']-packet['foreground_wait_started_monotonic_ns'])/1e6
  assert packet['published_monotonic_ns']<=packet['foreground_received_monotonic_ns']<=row['completed_monotonic_ns']
  a=row['worker_CPU_before'];b=row['worker_CPU_after'];delta=b['total_CPU_ticks']-a['total_CPU_ticks']
  assert a['PID']==b['PID'] and a['starttime_ticks']==b['starttime_ticks'] and a['nice']==b['nice']==10 and delta==row['worker_CPU_tick_delta']>=0
  assert a['clock_ticks_per_second']==b['clock_ticks_per_second']==100
  assert a['snapshot_finished_monotonic_ns']<=row['started_monotonic_ns']<=b['snapshot_started_monotonic_ns']<=b['snapshot_finished_monotonic_ns']<=row['completed_monotonic_ns']
  if run['policy']=='idle_gate':assert a['state']==b['state']=='T'
  CPUticks+=delta;CPUpositive+=delta>0;CPUwindows+=1
 if run['policy']=='idle_gate':
  assert len(pauses)==len(rows)
  for interval,row in zip(pauses,rows):assert interval['pause_acknowledged_monotonic_ns']<=row['started_monotonic_ns']<=row['completed_monotonic_ns']<=interval['resume_sent_monotonic_ns']
 else:assert pauses==[]
 bg=load(folder/'background/record.json');bt=load(folder/'background/terminal.json');enqueued=load(folder/'enqueued_identity_jobs.json')
 assert bg['status']==bt['status']=='ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE' and bt['record_sha256']==sha(folder/'background/record.json')
 assert bg['execution_policy']==run['policy'] and bg['actual_nice']==10 and bg['actual_CPU_affinity']==[0,1] and len(bg['jobs'])==len(enqueued)==case['actual_background_jobs']
 for job,request in zip(bg['jobs'],enqueued):
  assert job['event']==request['event'] and job['source_frame0']==request['source_frame0'] and job['selection']==request['selection']
  assert job['event'] in case['periodic_events'];candidates+=verify_selection(job['selection'],processed,post)
  assert job['queue_wait_ms']==(job['started_monotonic_ns']-job['enqueued_monotonic_ns'])/1e6
  assert job['enqueue_to_result_ms']==(job['completed_monotonic_ns']-job['enqueued_monotonic_ns'])/1e6
 jobs+=len(bg['jobs'])
 cases.append({'run':run['run'],'policy':run['policy'],'repeat':run['repeat'],'processed':len(rows),'skipped':len(skips),'late':case['deadline_misses'],'count_down':case['source_down_count'],
  'FPS':case['processed_per_second_over_offered_duration'],'P95_release_to_frontend_ms':float(np.quantile([r['release_to_count_ms'] for r in rows],.95)),
  'mean_model_ms':float(np.mean([r['model_ms'] for r in rows])),'actual_identity_jobs':len(bg['jobs']),'accepted_predictions':sum(j['accepted'] for j in bg['jobs']),
  'max_queue_wait_ms':max(j['queue_wait_ms'] for j in bg['jobs']),'max_enqueue_to_result_ms':max(j['enqueue_to_result_ms'] for j in bg['jobs']),
  'CPU_windows_positive_ticks':CPUpositive,'sum_child_CPU_ticks':CPUticks,'clock_ticks_per_second':100})
assert ticks==8598 and paths==8 and source_records==1568 and jobs==39 and CPUwindows==1466
result={'status':'UART_RECOVERED_METADATA_COUNTER_TIMING_SOURCE_CPU_AND_JOB_RECORDS_RECOMPUTED_PHOTOS_RAW_VECTORS_PENDING',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'metadata_archive_SHA256':meta['sha256'],'metadata_archive_members':95,
 'original_manifest_files_present_verified':len(present),'original_manifest_files_absent':missing,'counter_observation_ticks':ticks,'counter_paths':paths,
 'released_source_records':source_records,'actual_job_metadata':jobs,'frame_CPU_windows':CPUwindows,'selection_candidates_checked':candidates,'cases':cases,
 'all_actual_detection_raw_arrays_verified':False,'actual_photo_pixels_verified':False,'actual_input_tensors_and_features_verified':False,
 'complete_delivery_received':False,'new_model_forwards':0,'production_default_changed':False,'whole_goal_complete':False}
f=ROOT/'results/UART_metadata_audit.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['original_manifest_files_absent']}))
