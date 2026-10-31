from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,ast,subprocess,sys,tarfile,shutil
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
 assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
oldroot=PROJECT/'causal_photo_20261030';old=load(oldroot/'protocol/run_v1.json');sourcefile=oldroot/'tools/board_causal_repeats.py';source=sourcefile.read_text(encoding='utf-8')
def replace(old,new):
 global source
 assert source.count(old)==1,(old,source.count(old));source=source.replace(old,new)
replace('from causal_selector import CausalSelector, MAX_AGE_FRAMES, MAX_FRAMES','from causal_selector import CausalSelector, MAX_AGE_FRAMES, MAX_FRAMES\nfrom jpeg_producer import JPEGProducer')
replace('graph=lock=None;child=None;failure=None;close_error=None','graph=lock=None;child=None;producer=None;failure=None;close_error=None')
replace("concurrent=case in ['current_frame','causal_ring'];idle_gated=concurrent;causal=case=='causal_ring';requests=ready=None", "concurrent=True;idle_gated=True;causal=True;asynchronous=case=='async_input';requests=ready=None")
replace('t0=time.monotonic_ns()+100000000;slot=0;worker_pauses=[]', """t0=time.monotonic_ns()+100000000;slot=0;worker_pauses=[];input_packets=[]
   if asynchronous:
    producer=JPEGProducer([camera_byframe[r['frame0']] for r in selected],p['camera_root'],t0,deadline);producer.start()""")
replace("frame=selected[slot]['frame0'];start=time.monotonic_ns();actual=graph.run_image(framebank[slot]).copy();state['actual_O8_forwards']+=1", """frame=selected[slot]['frame0'];start=time.monotonic_ns()
    if producer:producer.pin(frame)
    actual=graph.run_image(framebank[slot]).copy();state['actual_O8_forwards']+=1""")
replace("read_start=time.monotonic_ns();jpeg_ring[frame]=(Path(p['camera_root'])/camera_byframe[frame]['file']).read_bytes()\n     jpeg_read_ms=(time.monotonic_ns()-read_start)/1e6", """read_start=time.monotonic_ns()
     if producer:
      packet=producer.take(frame);jpeg_ring[frame]=packet['payload'];packet_record=dict(packet['record']);packet_record['source']='async_producer'
     else:
      jpeg_ring[frame]=(Path(p['camera_root'])/camera_byframe[frame]['file']).read_bytes();read_finished=time.monotonic_ns()
      digest=hashlib.sha256(jpeg_ring[frame]).hexdigest();verified=time.monotonic_ns();assert digest==camera_byframe[frame]['sha256']
      packet_record={'slot':slot,'frame0':frame,'release_monotonic_ns':release,'read_started_monotonic_ns':read_start,'read_finished_monotonic_ns':read_finished,
       'verified_monotonic_ns':verified,'published_monotonic_ns':verified,'JPEG_bytes':len(jpeg_ring[frame]),'JPEG_sha256':digest,'source':'serial_foreground'}
     input_arrived=time.monotonic_ns();jpeg_read_ms=(input_arrived-read_start)/1e6
     assert packet_record['frame0']==frame and packet_record['read_started_monotonic_ns']>=release and packet_record['published_monotonic_ns']<=input_arrived
     input_packets.append({**packet_record,'foreground_wait_started_monotonic_ns':read_start,'foreground_received_monotonic_ns':input_arrived})""")
replace("'JPEG_frontend_read_ms':jpeg_read_ms,'selector_ms':selector_ms,'ring_frames':len(jpeg_ring),'ring_compressed_bytes':ring_bytes}", "'JPEG_frontend_read_ms':jpeg_read_ms,'selector_ms':selector_ms,'ring_frames':len(jpeg_ring),'ring_compressed_bytes':ring_bytes,\n      'JPEG_packet_source':packet_record['source'],'JPEG_input_received_monotonic_ns':input_arrived}")
replace("   if concurrent:\n    os.kill(child.pid,signal.SIGCONT)\n    requests.put(None)", """   if producer:
    producer_record=producer.finish(timeout=30);assert len(producer_record['records'])==392 and producer_record['pinned_at_end'] is None
    producer=None
   else:producer_record={'status':'SERIAL_INPUT_NO_PRODUCER','thread_alive':False,'records':[]}
   write(folder/'input_packets.json',input_packets);write(folder/'producer_record.json',producer_record)
   if concurrent:
    os.kill(child.pid,signal.SIGCONT)
    requests.put(None)""")
replace("'ring_peak_compressed_bytes':ring_peak_bytes,'enqueued_JPEG_payload_bytes_total':enqueued_payload_bytes,'cumulative_parent_proc_status':Path('/proc/self/status').read_text()}", "'ring_peak_compressed_bytes':ring_peak_bytes,'enqueued_JPEG_payload_bytes_total':enqueued_payload_bytes,\n    'producer_read_frames':len(producer_record['records']),'producer_thread_terminal':not producer_record['thread_alive'],\n    'cumulative_parent_proc_status':Path('/proc/self/status').read_text()}")
replace("assert len(state['cases'])==6", "assert len(state['cases'])==4")
replace("'ALL_SIX392_SLOT_CAUSAL_PHOTO_SAME_BOARD_REPEATS_COMPLETE'", "'ALL_FOUR392_SLOT_SERIAL_ASYNC_HIGHRES_SAME_BOARD_REPEATS_COMPLETE'")
replace(" finally:\n  if child is not None:", """ finally:
  if producer is not None:
   try:state['producer_after_failure']=producer.close(timeout=30)
   except BaseException as e:state['producer_close_error']=repr(e);state['producer_thread_still_alive']=producer.thread.is_alive()
  if child is not None:""")
runner=ROOT/'tools/board_async_repeats.py';assert not runner.exists();ast.parse(source);runner.write_text(source,encoding='utf-8')
for name in ['background_selected_worker.py','causal_selector.py']:shutil.copyfile(oldroot/'tools'/name,ROOT/'tools'/name)
test=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools/test_producer.py')],capture_output=True,text=True);assert test.returncode==0,test.stderr
save(ROOT/'results/producer_behavior_tests.json',json.loads(test.stdout))
keys=['video','tracker_config','counter_kwargs','registered_IDs','fixed_identity_threshold','backend_nice_increment','foreground_source_model','background_encoder','O8_bit_sha256','runtime_files','camera_root','graph_sha256','resident_plan_sha256','identity_preprocessing','identity_vector_protocol_sha256','selector']
p={k:old[k] for k in keys};names=['board_async_repeats.py','background_selected_worker.py','causal_selector.py','jpeg_producer.py','test_producer.py']
p.update({'status':'FROZEN_BEFORE_SERIAL_ASYNC_FULL_PIPELINE_FOUR_RUNS','created_UTC':datetime.now(timezone.utc).isoformat(),'period_ns':200000000,
 'cases':['serial_input','async_input'],'runs':[{'run':n,'policy':c,'repeat':r} for n,c,r in [('r1_serial_input','serial_input',1),('r1_async_input','async_input',1),('r2_async_input','async_input',2),('r2_serial_input','serial_input',2)]],
 'source_frame0_first':8915,'source_frame0_last':10870,'offered_slots_per_case':392,'scope_source_frames_inclusive':[8912,10873],
 'PNG_compress_level':0,'plan_sha256':sha(ROOT/'计划与验收.md'),'source_runner_sha256':sha(sourcefile),
 'payload_files':[{'file':name,'sha256':sha(ROOT/'tools'/name),'bytes':(ROOT/'tools'/name).stat().st_size} for name in names],
 'model_or_calibration_changed':False,'selector_or_counter_or_identity_threshold_changed':False,
 'both_modes_verify_each_acquired_JPEG':True,'async_producer_reads_every_released_source_frame':True,'serial_reads_only_processed_frames':True,
 'producer_release_gated_no_future_reads':True,'producer_cleaned_payload_bank_maximum':7,'producer_transient_maximum_including_new_read':8,
 'foreground_ring_cleaned_maximum':6,'queue_payload_and_decoded_image_memory_additional':True,
 'lowres192_is_ready_replay_not_derived_from_current_JPEG_at_runtime':True,'timing_from_global_lowres_release_includes_wait_for_actual_highres_acquisition':True,
 'hypothesis':'Actual_input_reads_can_overlap_detector_compute_without_future_frame_prefetch_or_excluding_input_wait',
 'simulated_RFID_all_unread':True,'actual_camera_or_RFID_hardware':False,'same_replay_repeats_not_independent_sessions':True,
 'global_cache_or_swap_controls':False,'new_training_updates':0,'new_independent_test':False,'whole_goal_complete':False})
save(ROOT/'protocol/run_v1.json',p)
a=ROOT/'payload_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
 tar.add(ROOT/'protocol/run_v1.json',arcname='run_protocol.json')
 for name in names:tar.add(ROOT/'tools'/name,arcname=name)
meta={'bytes':a.stat().st_size,'sha256':sha(a),'protocol_sha256':sha(ROOT/'protocol/run_v1.json'),'members':6};save(ROOT/'results/payload_manifest.json',meta)
remote='/home/xilinx/jupyter_notebooks/cow_research_async_highres_20261030'
launch='''set -euo pipefail
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,tarfile,hashlib,subprocess,sys,os,fcntl
root=Path('REMOTE');assert not (root/'launch.json').exists() and not (root/'results').exists()
prior=Path('/home/xilinx/jupyter_notebooks/cow_research_input_cost_v2_20261030/results/terminal.json');t=json.loads(prior.read_text());assert not (Path('/proc')/str(t['PID'])).exists()
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
a=root/'payload_v1.tar.gz';assert hashlib.sha256(a.read_bytes()).hexdigest()=='ARCHIVE_SHA'
allowed=['run_protocol.json','board_async_repeats.py','background_selected_worker.py','causal_selector.py','jpeg_producer.py','test_producer.py']
with tarfile.open(a) as tar:
 assert len(tar.getmembers())==6
 for m in tar.getmembers():
  assert m.isfile() and m.name in allowed
  f=root/m.name;assert not f.exists();f.write_bytes(tar.extractfile(m).read())
assert hashlib.sha256((root/'run_protocol.json').read_bytes()).hexdigest()=='PROTOCOL_SHA'
test=subprocess.run([sys.executable,'-B',str(root/'test_producer.py')],cwd=root,capture_output=True,text=True);assert test.returncode==0,test.stderr
(root/'board_producer_behavior_tests.json').write_text(test.stdout)
with (root/'run.log').open('xb') as log:child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_async_repeats.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'runs':4,'offered_slots_each':392,'firmware_changed':False};(root/'launch.json').write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r))
PY
'''.replace('REMOTE',remote).replace('ARCHIVE_SHA',meta['sha256']).replace('PROTOCOL_SHA',meta['protocol_sha256'])
(ROOT/'tools/launch.sh').write_text(launch,encoding='utf-8')
print(json.dumps({'status':p['status'],'producer_behavior_tests_passed':True,**meta}))
