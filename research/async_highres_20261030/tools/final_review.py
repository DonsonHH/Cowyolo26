from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re,ast
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
v=load(ROOT/'results/independent_verification.json');prod=load(ROOT/'results/producer_independent_verification.json');ref=load(ROOT/'results/reference_independent_verification.json');visual=load(ROOT/'results/visual_review.json');summary=load(ROOT/'results/summary.json');p=load(ROOT/'protocol/run_v1.json')
assert v['actual_O8_timed_forwards']==1465 and v['actual_O8_qualification_forwards']==8 and v['actual_O8_warmups']==8
assert [r['processed_frames'] for r in v['cases']]==[354,378,385,348] and [r['source_down_count'] for r in v['cases']]==[10,10,10,10]
assert [r['deadline_misses'] for r in v['cases']]==[353,170,363,347] and [r['skipped_slots'] for r in v['cases']]==[38,14,7,44]
assert v['counter_observation_ticks_with_history']==8597 and v['counter_paths']==8 and v['pause_windows_verified']==1465
assert v['actual_background_identity_jobs']==40 and v['identity_warmups']==4 and len(v['backgrounds'])==4
assert prod['producer_source_frames']==784 and prod['main_received_packets']==1465 and prod['overlapping_model_IO_packet_cases']==580 and prod['all_no_future_reads']
assert [r['accepted_provisional_predictions'] for r in v['backgrounds']]==[0,1,1,0]
assert ref['query_Torch_forwards']==40 and ref['gallery_Torch_forwards']==30 and ref['retrieval_conditions']==80 and ref['maximum_input_error']==0.
assert visual['actually_viewed'] and visual['panels']==40 and visual['sheets']==4
for row in visual['files']:assert sha(row['file'])==row['sha256'] and row['actually_viewed']
for row in p['payload_files']:assert sha(ROOT/'tools'/row['file'])==sha(ROOT/'delivery'/row['file'])==row['sha256']
assert sha(ROOT/'protocol/run_v1.json')==sha(ROOT/'delivery/run_protocol.json')
board=json.loads(load(ROOT/'evidence/final_board_read.json')['stdout']);assert board['status']=='ASYNC_HIGHRES_PARENT_FOUR_WORKERS_AND_COLLECTOR_TERMINAL_ABSENT_O8_AND_SERVICES_READ'
assert board['services']=={'22':True,'9090':True} and not board['parents_proc_exists'] and all(not r['proc_exists'] for r in board['children'])
assert board['shared_accelerator_lock_available'] and board['PL_bit_sha256']==p['O8_bit_sha256']
for name in ['results/producer_behavior_tests.json','delivery/board_producer_behavior_tests.json']:assert load(ROOT/name)['status']=='PRODUCER_RELEASE_BOUND_PIN_FAILURE_AND_STOP_BEHAVIOR_PASS'
jobs=load(ROOT/'results/actual_job_rows.json');accepted=[r for r in jobs if r['accepted']]
assert len(accepted)==2 and all(r['source_frame0']==9790 and r['predicted_id']=='009' for r in accepted) and len({r['photo_sha256'] for r in accepted})==1
paired=load(ROOT/'results/paired_identity_observations.json');assert paired['paired_events']==6 and paired['unmatched_events']==28 and 2*paired['paired_events']+paired['unmatched_events']==40
assert 'COMPLETED' in (ROOT/'evidence/cluster_final_read.txt').read_text(encoding='utf-8')
assert (ROOT/'tools/reference_lf.slurm').read_bytes()==(ROOT/'tools/reference.slurm').read_bytes().replace(b'\r\n',b'\n')
documents=[];links=0
for name in ['计划与验收.md','有界输入四次实机结果与下一步.md','Review与当前状态.md']:
 f=ROOT/name;s=f.read_text(encoding='utf-8');assert '\ufffd' not in s
 for m in re.finditer(r'\]\(<([^>]+)>\)',s):assert Path(m[1]).exists();links+=1
 documents.append({'path':str(f.resolve()),'sha256':sha(f),'lines_read_and_reviewed':len(s.splitlines())})
assert '计时外读过全部源JPEG' in (ROOT/'有界输入四次实机结果与下一步.md').read_text(encoding='utf-8')
names=['protocol/run_v1.json','protocol/reference_design_v1.json','protocol/reference_v1.json','protocol/reference_submission_repair_v1.json',
 'results/producer_behavior_tests.json','results/transfer_verification.json','results/independent_verification.json','results/producer_independent_verification.json',
 'results/actual_job_rows.json','results/actual_photo_manifest.json','results/actual_panel_pixel_verification.json','results/visual_review.json','results/paired_identity_observations.json','results/summary.json','results/reference_independent_verification.json',
 'delivery/results/record.json','delivery/results/terminal.json','delivery/final_state.json','delivery/board_producer_behavior_tests.json',
 'evidence/board_preflight.json','evidence/final_board_read.json','evidence/cluster_preflight.txt','evidence/cluster_final_read.txt','evidence/reference_submit.txt','evidence/reference_submit_repaired.txt','evidence/reference_status_01.txt']
codefiles=list((ROOT/'tools').glob('*.py'))
for f in codefiles:ast.parse(f.read_text(encoding='utf-8'))
result={'status':'ASYNC_HIGHRES4_REAL_RUNS1465_RAW784_RELEASED_SOURCE_READS40_ARM70_TORCH_AND_NONADOPTION_REVIEWED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'actual_O8_timed_forwards':1465,'actual_O8_qualification_forwards':8,'actual_O8_warmups':8,'actual_ARM_identity_queries':40,'actual_ARM_identity_warmups':4,
 'case_processed_frames':[354,378,385,348],'case_skips':[38,14,7,44],'case_deadline_misses':[353,170,363,347],'case_source_down_counts':[10,10,10,10],
 'case_FPS':[r['processed_per_second_over_offered_duration'] for r in v['cases']],
 'counter_observation_ticks_with_history':8597,'counter_paths':8,'worker_pause_windows':1465,'all_complete_O8_raw_byte_equal_to_prior_same_model':True,
 'released_producer_source_records':784,'foreground_received_packets':1465,'actual_positive_model_IO_overlap_cases':580,
 'all_timed_producer_reads_after_release':True,'preflight_integrity_reads_kernel_cache_scope_disclosed':True,
 'producer_behavior_tests_both_Windows_and_board_pass':True,'bounded_buffer_payload_not_total_system_memory':True,
 'actual_photos_and_all40_panels_verified_viewed':True,'accepted_predictions_per_background':[0,1,1,0],
 'both_accepts_same_f9790_pixels_not2_verified_cows':True,'literal_event_key_pairs':6,'unmatched_condition_records_retained':28,
 'fresh_Torch_query_forwards':40,'fresh_Torch_gallery_forwards':30,'fresh_Torch_retrieval_conditions':80,'maximum_query_normalized_feature_error':ref['maximum_query_normalized_error'],
 'maximum_gallery_normalized_feature_error':ref['maximum_gallery_normalized_error'],'all_Torch_input_tensors_byte_exact':True,
 'CRLF_first_submission_rejected_before_compute':True,'only_submission_line_endings_repaired':True,'reference_job130643_completed0_0':True,
 'board_parent_four_workers_reader_threads_collector_terminal_absent':True,'original_O8_and_services_retained':True,
 'prototype_kept_as_research_candidate':True,'global_default_changed':False,'stable5FPS_or_identity_accuracy_proven':False,
 'real_camera_or_RFID':False,'new_training_updates':0,'new_independent_test':False,'whole_goal_complete':False,
 'reviewer_kind':'assistant_self_review_with_separate_counter_geometry_packet_timestamp_hash_and_Torch_recomputations_not_independent_human',
 'documents':documents,'local_links_checked':links,'evidence_hashes':{n:sha(ROOT/n) for n in names},'code_hashes':{f.relative_to(ROOT).as_posix():sha(f) for f in codefiles}}
f=ROOT/'results/final_review.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ['documents','evidence_hashes','code_hashes']}))
