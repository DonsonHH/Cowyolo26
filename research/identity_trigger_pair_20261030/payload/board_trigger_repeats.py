from pathlib import Path
import os,sys,json,gzip,hashlib,time,fcntl,multiprocessing,traceback,signal
os.environ['XILINX_XRT']='/usr';os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';sys.dont_write_bytecode=True
import cv2,numpy as np
from pynq import PL
ROOT=Path(__file__).resolve().parent
O8=Path('/home/xilinx/jupyter_notebooks/yolo26_optimization_8')
PORT=Path('/home/xilinx/jupyter_notebooks/cow_research_numpy_tracker_20261029')
VIDEO=Path('/home/xilinx/jupyter_notebooks/cow_research_mosaic192_video_20261030')
MODEL=Path('/home/xilinx/jupyter_notebooks/cow_research_o8_mosaic192_qual_20261030')
IDENTITY=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029')
sys.path[:0]=[str(O8),str(O8/'runtime_fast'),str(PORT),str(PORT/'source/lap-0.5.13')]
from native_graph import NativeGraph
from device_initialize import initialize
from board_runtime import decode
from frame_pipeline import FramePipeline
from background_selected_worker import worker
from causal_selector import CausalSelector, MAX_AGE_FRAMES, MAX_FRAMES
from jpeg_producer import JPEGProducer
from process_cpu import snapshot as worker_CPU_snapshot
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def gz(p):return json.loads(gzip.decompress(p.read_bytes()))
def canonical(x):return json.loads(json.dumps(x))
def write(p,x):
 temp=p.with_suffix(p.suffix+'.partial')
 with temp.open('w') as f:json.dump(x,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 temp.replace(p)
def savegz(p,x):
 with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write(json.dumps(x,separators=(',',':')).encode())
def main():
 p=load(ROOT/'run_protocol.json');out=ROOT/'results';out.mkdir(exist_ok=False);cv2.setNumThreads(1);initial_affinity=sorted(os.sched_getaffinity(0));assert initial_affinity==[0,1];os.sched_setaffinity(0,set(p['foreground_affinity']))
 state={'status':'RUNNING','PID':os.getpid(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
  'protocol_sha256':sha(ROOT/'run_protocol.json'),'actual_O8_forwards':0,'qualification_forwards':0,'warmup_forwards':0,'cases':[],
  'new_training_updates':0,'actual_camera_and_RFID_hardware':False,'whole_goal_complete':False,'foreground_main_thread_affinity':sorted(os.sched_getaffinity(0))}
 graph=lock=None;child=None;producer=None;failure=None;close_error=None
 try:
  for row in p['payload_files']:assert sha(ROOT/row['file'])==row['sha256']
  for row in p['runtime_files']:assert sha(row['file'])==row['sha256']
  it=load(IDENTITY/'vectors_results_v3/terminal.json');ir=load(IDENTITY/'vectors_results_v3/record.json')
  assert it['status']==ir['status']=='ALL132_ACTUAL_ARM_NCNN_VECTORS_PREPROCESS_AND_RETRIEVAL_PASS_FROZEN_GATES'
  assert it['record_sha256']==sha(IDENTITY/'vectors_results_v3/record.json') and not (Path('/proc')/str(it['PID'])).exists()
  vt=load(VIDEO/'results/terminal.json');vr=load(VIDEO/'results/record.json')
  assert vt['status']==vr['status']=='ALL2654_ACTUAL_O8_VIDEO_INPUTS_AND_REAL_ARM_COUNTER_PATHS_COMPLETE'
  assert vt['record_sha256']==sha(VIDEO/'results/record.json') and not (Path('/proc')/str(vt['PID'])).exists()
  assert vr['model_checkpoint_sha256']==p['foreground_source_model'] and vr['actual_anchor_integer_parity_bytes_exact']==8
  assert sha(PL.bitfile_name)==p['O8_bit_sha256']
  spec=p['video'];inputs=load(VIDEO/'board_input_manifest.json');selected=[r for r in inputs if r['scene']=='original' and 8912<=r['frame0']<=10873]
  assert len(selected)==392
  framebank=np.empty((392,192,192,3),np.uint8)
  for i,row in enumerate(selected):
   file=VIDEO/row['file'];assert sha(file)==row['sha256'];framebank[i]=cv2.imread(str(file));assert framebank[i].shape==(192,192,3)
  camera_manifest=load(Path(p['camera_root'])/'manifest.json');camera_byframe={r['frame0']:r for r in camera_manifest}
  for row in camera_manifest:assert sha(Path(p['camera_root'])/row['file'])==row['sha256']
  lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  state['initialization']=initialize(O8)
  graph=NativeGraph(192,program=str(MODEL/'program'),plan=str(MODEL/'resident_plan/resident_plan.bin'),options=4,firmware_manifest='hardware/accepted/firmware_manifest.json')
  vector_gate=[]
  for row in [r for r in inputs if r['anchor']]:
   image=cv2.imread(str(VIDEO/row['file']));actual=graph.run_image(image).copy();state['qualification_forwards']+=1
   with np.load(VIDEO/'native_integer_anchors'/(row['scene']+'_f'+str(row['frame0'])+'.npz')) as a:assert actual.tobytes()==a['native_integer_raw'].tobytes()
   vector_gate.append({'scene':row['scene'],'frame0':row['frame0'],'BGR_input_to_complete_O8_raw_byte_exact':True})
  state['BGR_actual_vector_gate']=vector_gate;assert len(vector_gate)==8
  old_records=gz(VIDEO/'results/original/raw_predictions.json.gz');old_byframe={r['frame0']:r for r in old_records}
  old_trace=gz(VIDEO/'results/original/stride5_counter_trace.json.gz');old_raw=np.load(VIDEO/'results/original/all_raw.npy',mmap_mode='r')
  for run_spec in p['runs']:
   case=run_spec['policy'];run_name=run_spec['run'];folder=out/run_name;folder.mkdir();pipeline=FramePipeline(spec,p['tracker_config'],p['counter_kwargs'])
   history={'observations':[],'post_tracker':[],'confirmed_only_events':[],'handoff_events':[]}
   for frame in range(0,8915,5):
    result=pipeline.update(frame,old_byframe[frame]['predictions']);history['observations'].append(result['observation'])
    for key in ['post_tracker','confirmed_only_events','handoff_events']:history[key].extend(result[key])
   for key in history:
    expected=[r for r in old_trace[key] if r['frame0']<8915]
    assert canonical(history[key])==expected,('prewarm_history',case,key)
   write(folder/'prewarm_history_gate.json',{'actual_board_cached_raw_history_ticks':1783,'all_observations_both_event_lists_and_post_boxes_exact':True,'new_frontend_model_forwards_in_history':0})
   for _ in range(2):graph.run_image(framebank[0]);state['warmup_forwards']+=1
   concurrent=True;idle_gated=case=='idle_gate';causal=True;asynchronous=True;requests=ready=None
   selector=CausalSelector();jpeg_ring={};ring_peak_bytes=0;enqueued_payload_bytes=0
   if concurrent:
    context=multiprocessing.get_context('spawn');requests=context.Queue(maxsize=16);ready=context.Queue(maxsize=2)
    child=context.Process(target=worker,args=(requests,ready,str(folder/'background'),str(Path(p['camera_root']).parent),{**p,'worker_idle_gated':idle_gated,'identity_model':run_spec['identity_model']}));child.start()
    status=ready.get(timeout=40);assert status['status']=='READY',status
   trace={k:list(v) for k,v in history.items()};rows=[];raws=[];raw_frames=[];skips=[];enqueued=[];counter=0;deadline=int(p['period_ns'])
   t0=time.monotonic_ns()+100000000;slot=0;worker_pauses=[];input_packets=[]
   if asynchronous:
    producer=JPEGProducer([camera_byframe[r['frame0']] for r in selected],p['camera_root'],t0,deadline);producer.start()
   while slot<392:
    release=t0+slot*deadline;now=time.monotonic_ns()
    if now<release:time.sleep((release-now)/1e9)
    now=time.monotonic_ns();newest=max(slot,int((now-t0)//deadline))
    if newest>slot:
     for missed in range(slot,min(newest,392)):skips.append({'slot':missed,'source_frame0':selected[missed]['frame0'],'release_monotonic_ns':t0+missed*deadline,'skip_observed_monotonic_ns':now})
     slot=newest
     if slot>=392:break
     release=t0+slot*deadline
    pause_request=pause_ack=None
    if idle_gated:
     pause_request=time.monotonic_ns();os.kill(child.pid,signal.SIGSTOP)
     stopped_pid,stopped_status=os.waitpid(child.pid,os.WUNTRACED)
     pause_ack=time.monotonic_ns();assert stopped_pid==child.pid and os.WIFSTOPPED(stopped_status)
    worker_CPU_before=worker_CPU_snapshot(child.pid)
    frame=selected[slot]['frame0'];start=time.monotonic_ns()
    if producer:producer.pin(frame)
    actual=graph.run_image(framebank[slot]).copy();state['actual_O8_forwards']+=1
    model_end=time.monotonic_ns();oriented=decode(actual,[1050,1440,3],.2,192)
    boxes=[{'xyxy':[float(v[1])+870,1440-float(v[2]),float(v[3])+870,1440-float(v[0])],'confidence':float(v[4]),'class':0} for v in oriented]
    result=pipeline.update(frame,boxes);trace['observations'].append(result['observation'])
    for key in ['post_tracker','confirmed_only_events','handoff_events']:trace[key].extend(result[key])
    jpeg_read_ms=selector_ms=0.;ring_bytes=0
    if concurrent:
     selection_start=time.monotonic_ns();selector.observe(frame,result['post_tracker']);selector_ms+=(time.monotonic_ns()-selection_start)/1e6
    if causal:
     read_start=time.monotonic_ns()
     if producer:
      packet=producer.take(frame);jpeg_ring[frame]=packet['payload'];packet_record=dict(packet['record']);packet_record['source']='async_producer'
     else:
      jpeg_ring[frame]=(Path(p['camera_root'])/camera_byframe[frame]['file']).read_bytes();read_finished=time.monotonic_ns()
      digest=hashlib.sha256(jpeg_ring[frame]).hexdigest();verified=time.monotonic_ns();assert digest==camera_byframe[frame]['sha256']
      packet_record={'slot':slot,'frame0':frame,'release_monotonic_ns':release,'read_started_monotonic_ns':read_start,'read_finished_monotonic_ns':read_finished,
       'verified_monotonic_ns':verified,'published_monotonic_ns':verified,'JPEG_bytes':len(jpeg_ring[frame]),'JPEG_sha256':digest,'source':'serial_foreground'}
     input_arrived=time.monotonic_ns();jpeg_read_ms=(input_arrived-read_start)/1e6
     assert packet_record['frame0']==frame and packet_record['read_started_monotonic_ns']>=release and packet_record['published_monotonic_ns']<=input_arrived
     input_packets.append({**packet_record,'foreground_wait_started_monotonic_ns':read_start,'foreground_received_monotonic_ns':input_arrived})
     for expired in list(jpeg_ring):
      if frame-expired>MAX_AGE_FRAMES:del jpeg_ring[expired]
     assert len(jpeg_ring)<=MAX_FRAMES and set(jpeg_ring)=={f for f,_ in selector.frames}
     ring_bytes=sum(len(b) for b in jpeg_ring.values());ring_peak_bytes=max(ring_peak_bytes,ring_bytes)
    for event in result['handoff_events']:
     counter+=1
     if concurrent:
      selection_start=time.monotonic_ns();selection=selector.choose(frame,event['track_id'])
      chosen=selection['selected'] if causal else selection['current'];selection['used_candidate']=chosen;selection['policy']=case
      selector_ms+=(time.monotonic_ns()-selection_start)/1e6
      selected_frame=chosen['frame0'];enqueued_ns=time.monotonic_ns()
      job={'event':event,'event_source_frame0':frame,'source_frame0':selected_frame,'box_native_xyxy':chosen['xyxy'],'selection':selection,
        'source_JPEG_sha256':camera_byframe[selected_frame]['sha256'],'release_monotonic_ns':release,'enqueued_monotonic_ns':enqueued_ns,'simulated_RFID_read':False}
      if causal:
       assert selected_frame in jpeg_ring;job['_jpeg_payload']=jpeg_ring[selected_frame];enqueued_payload_bytes+=len(job['_jpeg_payload'])
      requests.put_nowait(job);enqueued.append({k:v for k,v in job.items() if k!='_jpeg_payload'})
    raws.append(actual[0]);raw_frames.append(frame)
    if len(raws)%50==0:
     write(out/'progress.json',{'status':'RUNNING','PID':os.getpid(),'case':case,'run':run_name,'processed_slots_this_case':len(raws),'frame0':frame,'actual_O8_forwards':state['actual_O8_forwards']})
    worker_CPU_after=worker_CPU_snapshot(child.pid)
    assert worker_CPU_before['PID']==worker_CPU_after['PID']==child.pid and worker_CPU_before['starttime_ticks']==worker_CPU_after['starttime_ticks']
    assert worker_CPU_before['nice']==worker_CPU_after['nice']==10 and worker_CPU_after['total_CPU_ticks']>=worker_CPU_before['total_CPU_ticks']
    done=time.monotonic_ns()
    if idle_gated:
     os.kill(child.pid,signal.SIGCONT);resumed=time.monotonic_ns()
     worker_pauses.append({'slot':slot,'pause_requested_monotonic_ns':pause_request,'pause_acknowledged_monotonic_ns':pause_ack,
       'foreground_started_monotonic_ns':start,'foreground_completed_monotonic_ns':done,'resume_sent_monotonic_ns':resumed,'child_PID':child.pid})
    rows.append({'slot':slot,'frame0':frame,'release_monotonic_ns':release,'started_monotonic_ns':start,'completed_monotonic_ns':done,
      'model_ms':(model_end-start)/1e6,'after_model_to_count_ms':(done-model_end)/1e6,'processing_ms':(done-start)/1e6,
      'release_to_count_ms':(done-release)/1e6,'deadline_met':done<=release+deadline,'event_count_so_far':counter,
      'JPEG_frontend_read_ms':jpeg_read_ms,'selector_ms':selector_ms,'ring_frames':len(jpeg_ring),'ring_compressed_bytes':ring_bytes,
      'JPEG_packet_source':packet_record['source'],'JPEG_input_received_monotonic_ns':input_arrived,
      'worker_CPU_before':worker_CPU_before,'worker_CPU_after':worker_CPU_after,'worker_CPU_tick_delta':worker_CPU_after['total_CPU_ticks']-worker_CPU_before['total_CPU_ticks']})
    slot+=1
   stop=time.monotonic_ns();period_end=t0+392*deadline
   if stop<period_end:time.sleep((period_end-stop)/1e9)
   if producer:
    producer_record=producer.finish(timeout=30);assert len(producer_record['records'])==392 and producer_record['pinned_at_end'] is None
    producer=None
   else:producer_record={'status':'SERIAL_INPUT_NO_PRODUCER','thread_alive':False,'records':[]}
   write(folder/'input_packets.json',input_packets);write(folder/'producer_record.json',producer_record)
   if concurrent:
    if idle_gated:os.kill(child.pid,signal.SIGCONT)
    requests.put(None);child.join(timeout=90);assert not child.is_alive(),'Backgroundstillrunning;retainhandle'
    background=load(folder/'background/record.json');assert background['status']=='ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE' and len(background['jobs'])==background['model_forwards']==len(enqueued)
    for actual_job,job in zip(background['jobs'],enqueued):assert actual_job['event']==job['event'] and actual_job['source_frame0']==job['source_frame0']
    child=None
   assert len(rows)+len(skips)==392
   # Whole-frame integer parity to the prior real board run is outside the timed period.
   for frame,raw in zip(raw_frames,raws):assert raw.tobytes()==old_raw[frame//5].tobytes()
   np.savez_compressed(folder/'actual_raw.npz',frame0=np.asarray(raw_frames,np.int64),raw=np.stack(raws))
   savegz(folder/'counter_trace.json.gz',trace);write(folder/'worker_pause_intervals.json',worker_pauses);write(folder/'timing_rows.json',rows);write(folder/'skipped_slots.json',skips);write(folder/'enqueued_identity_jobs.json',enqueued)
   events=[e for e in trace['handoff_events'] if 8912<=e['frame0']<=10873]
   report={'case':case,'run':run_name,'repeat':run_spec['repeat'],'identity_model':run_spec['identity_model'],'offered_slots':392,'processed_frames':len(rows),'skipped_slots':len(skips),'deadline_misses':sum(not r['deadline_met'] for r in rows),
    'mean_processing_ms':float(np.mean([r['processing_ms'] for r in rows])),'P95_release_to_count_ms':float(np.quantile([r['release_to_count_ms'] for r in rows],.95)),
    'source_down_count':sum(e['direction']=='A->B' for e in events),'source_up_count':sum(e['direction']=='B->A' for e in events),
    'processed_per_second_over_offered_duration':len(rows)/78.4,'periodic_events':events,'actual_background_jobs':len(enqueued),
    'all_actual_O8_outputs_byte_exact_to_prior_real_video':True,'clock_start_monotonic_ns':t0,'period_end_monotonic_ns':period_end,
    'ring_peak_compressed_bytes':ring_peak_bytes,'enqueued_JPEG_payload_bytes_total':enqueued_payload_bytes,
    'producer_read_frames':len(producer_record['records']),'producer_thread_terminal':not producer_record['thread_alive'],
    'cumulative_parent_proc_status':Path('/proc/self/status').read_text()}
   state['cases'].append(report);write(out/'record.json',state);print(json.dumps(report),flush=True)
  assert len(state['cases'])==4
  state.update({'status':'ALL4_ACTUAL_COUNT_TRIGGER_OLD_NEW_NEW_OLD_ASYNC_CAUSAL_IDENTITY_RUNS_COMPLETE','hardware_status':graph.status()})
 except BaseException as e:failure=e;state.update({'status':'FAILED','error':repr(e),'traceback':traceback.format_exc()})
 finally:
  if producer is not None:
   try:state['producer_after_failure']=producer.close(timeout=30)
   except BaseException as e:state['producer_close_error']=repr(e);state['producer_thread_still_alive']=producer.thread.is_alive()
  if child is not None:
   if child.is_alive():
    try:os.kill(child.pid,signal.SIGCONT)
    except Exception:pass
    try:requests.put_nowait(None)
    except Exception:pass
    child.join(timeout=10)
   state['pending_background_child']={'PID':child.pid,'alive':child.is_alive()}
  try:
   if graph:graph.close()
  except BaseException as e:close_error=repr(e);state['status']='CLOSE_FAILED_DEVICE_STATE_UNCERTAIN'
  state['close_error']=close_error;state['PL_after']=PL.bitfile_name
  if PL.bitfile_name:state['PL_after_sha256']=sha(PL.bitfile_name)
  os.sched_setaffinity(0,set(initial_affinity));state['main_affinity_restored']=sorted(os.sched_getaffinity(0))
  state['memory_after']=Path('/proc/meminfo').read_text();write(out/'record.json',state);os.sync()
  write(out/'terminal.json',{'status':state['status'],'PID':os.getpid(),'actual_O8_forwards':state['actual_O8_forwards'],'record_sha256':sha(out/'record.json'),'close_error':close_error})
  if lock:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
 if failure or close_error:raise SystemExit(1)
if __name__=='__main__':main()
