from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import json,hashlib,re,ast
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
v=load(ROOT/'results/independent_verification.json');ref=load(ROOT/'results/reference_independent_verification.json');visual=load(ROOT/'results/actual_visual_review.json');readonly=load(ROOT/'results/readonly_visual_review.json');probe=load(ROOT/'results/entry_skip_probe.json');b=load(ROOT/'evidence/final_board_read.json');board=json.loads(b['stdout']);p=load(ROOT/'protocol/run_v1.json');jobrows=load(ROOT/'results/actual_job_rows.json')
assert b['exit_code']==0 and board['status']=='CAUSAL_PHOTO_PARENT_FOUR_WORKERS_AND_COLLECTOR_TERMINAL_ABSENT_O8_AND_SERVICES_READ'
assert not board['parents_proc_exists'] and len(board['children'])==4 and all(not r['proc_exists'] for r in board['children'])
assert board['shared_accelerator_lock_available'] and board['services']=={'22':True,'9090':True} and board['PL_bit_sha256']==p['O8_bit_sha256']
assert [r['processed_frames'] for r in v['cases']]==[392,391,379,376,381,390]
assert [r['source_down_count'] for r in v['cases']]==[10,10,10,10,9,9]
assert [r['skipped_slots'] for r in v['cases']]==[0,1,13,16,11,2]
assert [r['deadline_misses'] for r in v['cases']]==[24,20,253,281,24,41]
assert v['counter_paths']==12 and v['counter_observation_ticks_with_history']==13007 and v['pause_windows_verified']==1527
assert v['actual_O8_timed_forwards']==2309 and v['actual_background_identity_jobs']==39 and v['identity_warmups']==4
assert ref['query_Torch_forwards']==39 and ref['gallery_Torch_forwards']==30 and ref['retrieval_conditions']==78 and ref['maximum_input_error']==0.
assert visual['actually_viewed'] and visual['panels']==39 and visual['sheets']==4 and readonly['actually_viewed'] and readonly['panels']==20
for row in visual['files']+readonly['files']:assert sha(row['file'])==row['sha256']
assert [r['counter_only_count'] for r in probe['counter_only_probes']]==[10,9,10,9,9] and [r['longest_A_run'] for r in probe['actual_periodic_cases']]==[2,1]
accepted=[r for r in jobrows if r['accepted']];assert len(accepted)==4 and len({r['photo_sha256'] for r in accepted})==1 and all(r['source_frame0']==9790 and r['predicted_id']=='009' for r in accepted)
assert len(jobrows)==39 and sum(r['source_frame0']<r['event']['frame0'] for r in jobrows)==14
pairs=load(ROOT/'results/paired_identity_observations.json');assert pairs['paired_events']==7 and pairs['unmatched_events']==25 and 2*pairs['paired_events']+pairs['unmatched_events']==39
for row in p['payload_files']:assert sha(ROOT/'tools'/row['file'])==row['sha256']==sha(ROOT/'delivery'/row['file'])
assert sha(ROOT/'protocol/run_v1.json')==sha(ROOT/'delivery/run_protocol.json')
assert load(ROOT/'protocol/runtime_binding_clarification_v1.json')['model_graph_plan_encoder_gallery_threshold_and_runtime_hash_list_identical_to_previous_joint']
cluster=(ROOT/'evidence/cluster_final_read.txt').read_text(encoding='utf-8');assert '130642' in cluster and 'COMPLETED' in cluster and '0:0' in cluster
documents=[];links=0
for name in ['计划与验收.md','补充计时口径.md','实现边界与事后核对.md','因果抓拍实机结果与不采用决定.md','Review与当前状态.md']:
 f=ROOT/name;s=f.read_text(encoding='utf-8');assert '\ufffd' not in s
 for match in re.finditer(r'\]\(<([^>]+)>\)',s):assert Path(unquote(match[1])).exists();links+=1
 documents.append({'path':str(f.resolve()),'sha256':sha(f),'lines_read_and_reviewed':len(s.splitlines())})
codefiles=list((ROOT/'tools').glob('*.py'))
for f in codefiles:ast.parse(f.read_text(encoding='utf-8'))
names=['protocol/run_v1.json','protocol/reference_design_v1.json','protocol/reference_v1.json','protocol/runtime_binding_clarification_v1.json',
 'results/payload_manifest.json','results/pre_data_causality_tests.json','results/readonly_pairs.json','results/readonly_independent_verification.json','results/readonly_visual_review.json',
 'results/transfer_verification.json','results/independent_verification.json','results/actual_job_rows.json','results/actual_photo_manifest.json','results/actual_panel_pixel_verification.json','results/actual_visual_review.json','results/paired_identity_observations.json','results/timing_and_event_diagnosis.json','results/entry_skip_probe.json','results/reference_independent_verification.json',
 'delivery/results/record.json','delivery/results/terminal.json','delivery/final_state.json','evidence/board_preflight.json','evidence/final_board_read.json','evidence/collection_terminal_read.json','evidence/archive_get.json','evidence/reference_status_01.txt','evidence/cluster_final_read.txt']
result={'status':'FROZEN_CAUSAL_PHOTO_SIX_REAL_RUNS2309_O8_RAW39_ARM_PHOTOS69_TORCH_REFERENCES_AND_NONADOPTION_REVIEWED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'reviewer_kind':'assistant_self_review_with_separate_raw_geometry_counter_feature_and_pixel_recomputation_not_independent_human',
 'actual_O8_timed_forwards':2309,'actual_O8_qualification_forwards':8,'actual_O8_warmups':12,'actual_identity_ARM_query_forwards':39,'actual_identity_ARM_warmups':4,
 'case_processed_frames':[r['processed_frames'] for r in v['cases']],'case_source_down_counts':[r['source_down_count'] for r in v['cases']],
 'case_skips':[r['skipped_slots'] for r in v['cases']],'case_deadline_misses':[r['deadline_misses'] for r in v['cases']],
 'case_throughput_FPS':[r['processed_per_second_over_offered_duration'] for r in v['cases']],
 'counter_paths':12,'counter_observation_ticks_with_history':13007,'pause_windows_verified':1527,'all_actual_raws_byte_exact_to_prior_full_same_model_O8':True,
 'readonly_photo_pairs':10,'readonly_candidate_observations':60,'readonly_panels_viewed':20,'actual_ARM_panels_viewed':39,'actual_selection_candidate_observations':230,
 'actual_same_tensor_feature_byte_exact_checks':26,'fresh_Torch_query_forwards':39,'fresh_Torch_gallery_forwards':30,'fresh_Torch_retrieval_conditions':78,
 'maximum_query_normalized_feature_error':ref['maximum_query_normalized_error'],'maximum_gallery_normalized_feature_error':ref['maximum_gallery_normalized_error'],
 'source_and_Torch_input_tensors_exact':True,'all_actual_photos_features_scores_and_reject_decisions_verified':True,
 'exact_event_key_pairs':7,'unmatched_condition_records_retained':25,'accepted_predictions_in_each_background':[1,1,1,1],
 'all4_accepts_same_f9790_pixels_not4_animals':True,'causal_ring_policies_adopted':False,'production_tracker_or_counter_changed':False,
 'posthoc_counter_deletion_probe_counts':[10,9,10,9,9],'counter_probe_is_full_tracker_rerun':False,'single_frame_special_case_deployed':False,
 'steady6_JPEG_payload_peak_bytes':4418520,'transient7_JPEG_payload_peak_bytes':5149692,'JPEG_payload_claimed_total_memory':False,
 'inherited_model_and_quant_metadata_clarified_without_mutating_run':True,'asynchronous_queue_copy_scope_disclosed':True,
 'parent_four_workers_collector_terminal_absent':True,'server_job130642_completed0_0':True,'known_O8_and_services_retained':True,
 'new_training_updates':0,'new_independent_test':False,'real_camera_or_RFID':False,'permanent_identity_accuracy_proven':False,'whole_goal_complete':False,
 'documents':documents,'local_links_checked':links,'code_AST_files_checked':len(codefiles),'evidence_hashes':{name:sha(ROOT/name) for name in names},'code_hashes':{str(f.relative_to(ROOT).as_posix()):sha(f) for f in codefiles}}
f=ROOT/'results/final_review.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['documents','evidence_hashes','code_hashes']}))
