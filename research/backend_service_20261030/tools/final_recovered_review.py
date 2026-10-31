from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re,ast
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def serial_object(path,status):
 r=load(path);assert r['status']=='SERIAL_COMMAND_COMPLETE' and r['exit_code']==0
 for line in r['output'].splitlines():
  try:v=json.loads(line)
  except json.JSONDecodeError:continue
  if isinstance(v,dict) and v.get('status')==status:return v
 raise AssertionError(('missing_serial_object',str(path),status))
v=load(ROOT/'results/UART_metadata_audit.json');recovery=load(ROOT/'results/recovery_independent_verification.json');ref=load(ROOT/'results/reference_independent_verification.json');visual=load(ROOT/'results/visual_review.json');s=load(ROOT/'results/summary_recovered.json');p=load(ROOT/'protocol/run_v1.json')
assert [r['processed'] for r in v['cases']]==[378,362,335,391] and [r['count_down'] for r in v['cases']]==[10,9,10,10]
assert [r['skipped'] for r in v['cases']]==[14,30,57,1] and [r['late'] for r in v['cases']]==[191,177,304,187]
assert v['counter_observation_ticks']==8598 and v['counter_paths']==8 and v['released_source_records']==1568 and v['frame_CPU_windows']==1466 and v['actual_job_metadata']==39
assert [r['CPU_windows_positive_ticks'] for r in v['cases']]==[0,48,46,0] and [r['sum_child_CPU_ticks'] for r in v['cases']]==[0,857,975,0]
assert recovery['original_board_manifest_files_read_and_hash_verified_on_board']==178 and recovery['actual_O8_raw_cases_verified_on_board_and_hash_bound_locally']==1466
assert recovery['photos_pixels_verified']==recovery['input_tensors_byte_exact']==recovery['raw_feature_bytes_bound_to_original_job_hashes']==39
assert recovery['reconstructed_PNG_files_byte_identical_to_board_PNGs']==30 and not recovery['original_full_archive_locally_downloaded']
assert ref['query_Torch_forwards']==39 and ref['gallery_Torch_forwards']==30 and ref['retrieval_conditions']==78 and ref['maximum_input_error']==0.
assert ref['job_id']=='130717' and 'COMPLETED' in (ROOT/'evidence/cluster_final_read.txt').read_text(encoding='utf-8')
assert visual['actually_viewed'] and visual['panels']==39 and visual['sheets']==4
for r in visual['files']:assert r['actually_viewed'] and sha(r['file'])==r['sha256']
for r in p['payload_files']:assert sha(ROOT/'tools'/r['file'])==r['sha256']
state=load(ROOT/'metadata_recovery/results/record.json');assert state['actual_O8_forwards']==1466 and state['qualification_forwards']==state['warmup_forwards']==8
final=serial_object(ROOT/'evidence/serial_final_recovery_state03.json','SERIAL_FINAL_RECOVERY_TASKS_ABSENT_LOCAL_SERVICES_UP_NO_CARRIER')
assert final['all_checked_PIDs_absent'] and len(final['checked_PIDs'])==7 and final['lock_available'] and final['local_services']=={'22':True,'9090':True}
assert final['eth0_carrier']=='0' and final['boot_id']==state['boot_id'] and final['full_archive_preserved']
assert final['current_bitfile_on_disk_sha256']==p['O8_bit_sha256']==final['collected_PL_state_sha256'] and final['current_loaded_PL_state_requeried'] is False
assert load(ROOT/'evidence/serial_final_recovery_state01.json')['exit_code']==1 and load(ROOT/'evidence/serial_final_recovery_state02.json')['exit_code']==1
pairs=load(ROOT/'results/paired_identity_observations.json');assert pairs['paired_events']==4 and pairs['unmatched_events']==31 and 2*4+31==39
jobs=load(ROOT/'results/actual_job_rows.json');accepted=[j for j in jobs if j['accepted']]
assert len(accepted)==3 and len({j['original_board_photo_SHA256'] for j in accepted})==1 and all(j['source_frame0']==9790 and j['predicted_id']=='009' for j in accepted)
normal=load(ROOT/'evidence/reconstruction_normalization_diagnosis.json');assert normal['same_prior_gate_passes_all'] and len(normal['locally_recomputed_normalization_not_bytes_equal_indices'])==16
assert normal['maximum_float64_reference_normalization_error']<1e-7
documents=[];links=0
for name in ['计划与验收.md','串口恢复与数值复核说明.md','后台服务四次实机结果与取舍.md','Review与当前状态.md']:
 f=ROOT/name;text=f.read_text(encoding='utf-8');assert '\ufffd' not in text
 for m in re.finditer(r'\]\(<([^>]+)>\)',text):assert Path(m[1]).exists();links+=1
 documents.append({'path':str(f.resolve()),'sha256':sha(f),'lines_read_and_reviewed':len(text.splitlines())})
assert '尚未完成本机下载' in (ROOT/'后台服务四次实机结果与取舍.md').read_text(encoding='utf-8')
evidence=['protocol/run_v1.json','protocol/reference_design_v1.json','protocol/reference_v1.json','results/UART_metadata_audit.json',
 'results/recovery_independent_verification.json','results/summary_recovered.json','results/actual_job_rows.json','results/actual_panel_pixel_verification.json','results/visual_review.json','results/paired_identity_observations.json','results/reference_independent_verification.json',
 'evidence/metadata_UART_transfer.json','evidence/numeric_UART_transfer.json','evidence/serial_recovery_inspect01.json','evidence/serial_audit_status01.json','evidence/serial_final_recovery_state01.json','evidence/serial_final_recovery_state02.json','evidence/serial_final_recovery_state03.json',
 'evidence/reconstruction_normalization_diagnosis.json','evidence/reference_submit.txt','evidence/reference_status_01.txt','evidence/cluster_final_read.txt',
 'metadata_recovery/results/record.json','metadata_recovery/results/terminal.json','metadata_recovery/result_manifest.json','metadata_recovery/final_state.json','metadata_recovery/transfer.json',
 'numeric_recovery/board_file_audit.json','numeric_recovery/recovered_photo_bindings.json','numeric_recovery/recovered_raw_bindings.json','numeric_recovery/recovered_actual_features.npz']
code=list((ROOT/'tools').glob('*.py'))
for f in code:ast.parse(f.read_text(encoding='utf-8'))
result={'status':'BACKEND_SERVICE4_REAL_RUNS1466_RAW39_PHOTOS69_TORCH_SERIAL_RECOVERY_REVIEWED_FULL_ARCHIVE_LOCAL_PENDING','created_UTC':datetime.now(timezone.utc).isoformat(),
 'actual_O8_timed_forwards':1466,'actual_O8_qualification_forwards':8,'actual_O8_warmups':8,'actual_ARM_identity_queries':39,'actual_ARM_identity_warmups':4,
 'fresh_Torch_query_forwards':39,'fresh_Torch_gallery_forwards':30,'fresh_Torch_retrieval_conditions':78,'reference_job130717_completed0_0':True,
 'case_processed_frames':[378,362,335,391],'case_skips':[14,30,57,1],'case_deadline_misses':[191,177,304,187],'case_source_down_counts':[10,9,10,10],
 'case_FPS':[r['FPS'] for r in v['cases']],'max_backend_completion_ms':[r['max_enqueue_to_result_ms'] for r in v['cases']],
 'counter_observation_ticks':8598,'counter_paths':8,'released_source_records':1568,'CPU_boundary_windows':1466,'CPU_positive_tick_windows':[0,48,46,0],'CPU_tick_sums':[0,857,975,0],
 'original_files_hash_verified_on_board':178,'complete_O8_raws_verified_on_board_and_hash_bound_locally':1466,
 'photo_pixels_and_input_tensors_verified':39,'actual_raw_features_hash_bound':39,'reconstructed_PNG_byte_identical':30,'remaining9_PNGs_pixels_equal_encoding_diff':True,
 'all39_photo_panels_viewed':True,'accepted_predictions_per_run':[1,1,0,1],'all3_accepts_same_f9790_not3_verified_cows':True,
 'literal_event_key_pairs':4,'unmatched_condition_records_retained':31,'same_preexisting_normalization_and_score_gates_used':True,'extra_byte_normalization_failure_preserved':True,
 'new_global_default_adopted':False,'stable5FPS_count12_or_identity_accuracy_proven':False,
 'full_original_archive_locally_downloaded':False,'full_original_archive_preserved_on_board':True,'raw_arrays_locally_downloaded':False,
 'UART_metadata_and_numeric_archives_hash_verified':True,'recovery_added_model_forwards':0,'recovery_reset_or_network_changes':False,
 'experiment_workers_collector_and_audit_PIDs_absent':True,'local_SSH_and_Jupyter_services_active':True,'ethernet_carrier':0,'external_SSH_and_Jupyter_access_recovered':False,
 'loaded_O8_checked_at_original_root_collection':True,'loaded_O8_rechecked_after_network_loss':False,'current_on_disk_bitfile_SHA_unchanged':True,'shared_accelerator_lock_available':True,
 'new_training_updates':0,'new_independent_test':False,'real_camera_or_RFID':False,'whole_goal_complete':False,
 'reviewer_kind':'assistant_self_review_with_separate_serial_onboard_and_local_hash_pixel_counter_feature_and_Torch_checks_not_independent_human',
 'documents':documents,'local_links_checked':links,'evidence_hashes':{n:sha(ROOT/n) for n in evidence},'code_hashes':{f.relative_to(ROOT).as_posix():sha(f) for f in code}}
f=ROOT/'results/final_review.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['documents','evidence_hashes','code_hashes']}))
