from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, tarfile, ast, subprocess, sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
 assert not p.exists();p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
source=PROJECT/'pynq_mosaic192_joint_20261030/tools/board_joint_repeats.py'
text=source.read_text(encoding='utf-8')
def replace(old,new):
 global text
 assert text.count(old)==1,(old,text.count(old));text=text.replace(old,new)
replace('from background_capture0_worker import worker','from background_selected_worker import worker\nfrom causal_selector import CausalSelector, MAX_AGE_FRAMES, MAX_FRAMES')
replace("for row in load(Path(p['camera_root'])/'manifest.json'):assert sha(Path(p['camera_root'])/row['file'])==row['sha256']", "camera_manifest=load(Path(p['camera_root'])/'manifest.json');camera_byframe={r['frame0']:r for r in camera_manifest}\n  for row in camera_manifest:assert sha(Path(p['camera_root'])/row['file'])==row['sha256']")
replace("concurrent=case in ['foreground_with_identity','foreground_idle_identity'];idle_gated=case=='foreground_idle_identity';requests=ready=None", "concurrent=case in ['current_frame','causal_ring'];idle_gated=concurrent;causal=case=='causal_ring';requests=ready=None\n   selector=CausalSelector();jpeg_ring={};ring_peak_bytes=0;enqueued_payload_bytes=0")
replace("    for event in result['handoff_events']:\n     counter+=1\n     if concurrent:\n      current=next(b for b in result['post_tracker'] if b['track_id']==event['track_id'])\n      enqueued_ns=time.monotonic_ns();job={'event':event,'source_frame0':frame,'box_native_xyxy':current['xyxy'],\n        'release_monotonic_ns':release,'enqueued_monotonic_ns':enqueued_ns,'simulated_RFID_read':False}\n      requests.put_nowait(job);enqueued.append(job)", """    jpeg_read_ms=selector_ms=0.;ring_bytes=0
    if concurrent:
     selection_start=time.monotonic_ns();selector.observe(frame,result['post_tracker']);selector_ms+=(time.monotonic_ns()-selection_start)/1e6
    if causal:
     read_start=time.monotonic_ns();jpeg_ring[frame]=(Path(p['camera_root'])/camera_byframe[frame]['file']).read_bytes()
     jpeg_read_ms=(time.monotonic_ns()-read_start)/1e6
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
      requests.put_nowait(job);enqueued.append({k:v for k,v in job.items() if k!='_jpeg_payload'})""")
replace("'release_to_count_ms':(done-release)/1e6,'deadline_met':done<=release+deadline,'event_count_so_far':counter}", "'release_to_count_ms':(done-release)/1e6,'deadline_met':done<=release+deadline,'event_count_so_far':counter,\n      'JPEG_frontend_read_ms':jpeg_read_ms,'selector_ms':selector_ms,'ring_frames':len(jpeg_ring),'ring_compressed_bytes':ring_bytes}")
replace("'all_actual_O8_outputs_byte_exact_to_prior_real_video':True,'clock_start_monotonic_ns':t0,'period_end_monotonic_ns':period_end}", "'all_actual_O8_outputs_byte_exact_to_prior_real_video':True,'clock_start_monotonic_ns':t0,'period_end_monotonic_ns':period_end,\n    'ring_peak_compressed_bytes':ring_peak_bytes,'enqueued_JPEG_payload_bytes_total':enqueued_payload_bytes,'cumulative_parent_proc_status':Path('/proc/self/status').read_text()}")
replace("'ALL_SIX392_SLOT_MOSAIC192_SAME_BOARD_REPEATS_COMPLETE'", "'ALL_SIX392_SLOT_CAUSAL_PHOTO_SAME_BOARD_REPEATS_COMPLETE'")
file=ROOT/'tools/board_causal_repeats.py';assert not file.exists();ast.parse(text);file.write_text(text,encoding='utf-8')
test=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools/test_causality.py')],capture_output=True,text=True);assert test.returncode==0,test.stderr
save(ROOT/'results/pre_data_causality_tests.json',json.loads(test.stdout))
p=json.loads((PROJECT/'pynq_mosaic192_joint_20261030/protocol/run_v1.json').read_text(encoding='utf-8'))
p.update({'status':'FROZEN_BEFORE_LOCAL_PHOTO_SELECTION_AND_SIX_BOARD_RUNS','created_UTC':datetime.now(timezone.utc).isoformat(),
 'previous_protocol_sha256':sha(PROJECT/'pynq_mosaic192_joint_20261030/protocol/run_v1.json'),
 'cases':['foreground_only','current_frame','causal_ring'],
 'runs':[{'run':name,'policy':policy,'repeat':repeat} for name,policy,repeat in [
 ('r1_foreground_only','foreground_only',1),('r1_current_frame','current_frame',1),('r1_causal_ring','causal_ring',1),
 ('r2_causal_ring','causal_ring',2),('r2_current_frame','current_frame',2),('r2_foreground_only','foreground_only',2)]],
 'selector':{'maximum_age_frames_at25fps':25,'maximum_compressed_JPEG_frames':6,'edge_guard_px':16,
 'formula':'visible_box_area*(1-max_other_confirmed_box_intersection_fraction)*min(1,max(0,minimum_ROI_edge_margin)/16)',
 'ties':'Most_recent_available_frame','uses_future_frames':False,'uses_identity_labels_or_gallery_scores':False,'uses_highres_pixels_to_rank':False,
 'candidate_evidence':'Only_current_or_past_actual_processed_confirmed_post_tracker_rows_of_same_temporary_ID'},
 'timing_scope':'Detector_input_is_ready192BGR_replay;causal_policy_adds_per_processed_frame_actual_highres_JPEG_file_read_ring_and_queue_payload;not_exposure_or_live_camera',
 'treatment_comparison':'Current_frame_backend_file_read_vs_causal_compressed_ring_plus_geometry_selection;combined_policy_not_pure_scoring_causality',
 'photo_selector_candidate_count':1,'new_identity_threshold_tuning':False,'new_independent_test':False,
 'fixed_intervention':'One_frozen_past_only_geometry_photo_selector_and_actual_bounded_compressed_ring',
 'build_source':{'file':str(source.resolve()),'sha256':sha(source)},
 'plan_sha256':sha(ROOT/'计划与验收.md'),
 'payload_files':[{'file':name,'sha256':sha(ROOT/'tools'/name),'bytes':(ROOT/'tools'/name).stat().st_size} for name in ['board_causal_repeats.py','background_selected_worker.py','causal_selector.py']],
 'local_readonly_source':{'trace':str((PROJECT/'pynq_mosaic192_eval_20261030/board_delivery/results/original/stride5_counter_trace.json.gz').resolve()),
 'trace_sha256':sha(PROJECT/'pynq_mosaic192_eval_20261030/board_delivery/results/original/stride5_counter_trace.json.gz'),
 'camera_manifest_sha256':sha(PROJECT/'pynq_periodic_joint_20261030/camera_delivery/manifest.json')}})
save(ROOT/'protocol/run_v1.json',p)
archive=ROOT/'payload_v1.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 tar.add(ROOT/'protocol/run_v1.json',arcname='run_protocol.json')
 for row in p['payload_files']:tar.add(ROOT/'tools'/row['file'],arcname=row['file'])
save(ROOT/'results/payload_manifest.json',{'created_UTC':datetime.now(timezone.utc).isoformat(),'sha256':sha(archive),'bytes':archive.stat().st_size,'members':4,'protocol_sha256':sha(ROOT/'protocol/run_v1.json'),'first_selection_or_new_board_forwards_not_yet_run':True})
print(json.dumps({'status':p['status'],'payload_sha256':sha(archive),'protocol_sha256':sha(ROOT/'protocol/run_v1.json')}))
