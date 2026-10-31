from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
v=load(ROOT/'results/independent_verification.json');visual=load(ROOT/'results/visual_review.json')
p=load(ROOT/'protocol/run_v1.json');final_read=load(ROOT/'evidence/final_board_read.json');board=json.loads(final_read['stdout'])
assert board['status']=='THREE_NEW_PARENT_TASKS_FOUR_IDENTITY_WORKERS_TERMINAL_ABSENT_O8_AND_SERVICES_READ'
assert board['shared_accelerator_lock_available'] and all(not r['proc_exists'] for r in board['tasks']+board['children'])
assert board['services']=={'22':True,'9090':True} and board['PL_bit_sha256']==p['O8_bit_sha256']
assert len(v['cases'])==6 and v['counter_paths']==12 and v['actual_O8_qualification_forwards']==8 and v['actual_O8_warmups']==12
assert v['actual_O8_timed_forwards']==sum(r['processed_frames'] for r in v['cases'])
assert v['counter_observation_ticks_with_history']==6*1783+v['actual_O8_timed_forwards']
assert v['actual_background_identity_jobs']==sum(r['actual_background_jobs'] for r in v['cases']) and v['identity_warmups']==4
assert v['pause_windows_verified']==sum(r['processed_frames'] for r in v['cases'] if r['case']=='foreground_idle_identity')
assert v['all_runtime_photos_inputs_features_scores_recomputed'] and v['parent_and_four_background_workers_terminal_absent']
assert visual['actually_viewed_photo_panels']==v['actual_background_identity_jobs']
for row in visual['files']:assert row['actually_viewed'] and sha(row['path'])==row['sha256']
quant=load(ROOT/'results/new_input_quant256_equivalence.json');assert quant['divide_vs_multiply_quantized_codes_exact'] and len(quant['codes'])==256
assert quant['new_model_rechecked_after_launch_without_mutating_running_protocol']
documents=[];links=0
for name in ['计划与验收.md','新候选同板周期与两轮复测.md','Review与当前状态.md']:
    f=ROOT/name;text=f.read_text(encoding='utf-8');assert '\ufffd' not in text
    for match in re.finditer(r'\]\(<([^>]+)>\)',text):assert Path(unquote(match[1])).exists();links+=1
    documents.append({'path':str(f.resolve()),'sha256':sha(f),'lines_read_and_reviewed':len(text.splitlines())})
evidence=['protocol/run_v1.json','results/independent_verification.json','results/new_input_quant256_equivalence.json','results/visual_review.json',
    'results/photo_panels/manifest.json','delivery/results/record.json','delivery/results/terminal.json','delivery/final_state.json',
    'evidence/payload.json','evidence/board_launch.json','evidence/collection.json','evidence/collection_inspection01.json',
    'evidence/collection_complete_read.json','evidence/transfer.json','evidence/final_board_read.json','evidence/cluster_final_read.txt',
    'tools/board_joint_repeats.py','tools/background_capture0_worker.py','tools/verify_results.py','tools/make_photo_panels.py']
result={'status':'NEW_MOSAIC192_SIX_REAL_PERIODIC_RUNS_ALL_RAW_PHOTOS_AND_RETRIEVALS_REVIEWED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'checkpoint_sha256':p['foreground_source_model'],'actual_O8_timed_forwards':v['actual_O8_timed_forwards'],
    'actual_O8_qualification_forwards':8,'actual_O8_warmups':12,'six_run_order':[r['run'] for r in v['cases']],
    'case_processed_frames':[r['processed_frames'] for r in v['cases']],'case_skips':[r['skipped_slots'] for r in v['cases']],
    'case_deadline_misses':[r['deadline_misses'] for r in v['cases']],'case_source_down_counts':[r['source_down_count'] for r in v['cases']],
    'case_throughput_FPS':[r['processed_per_second_over_offered_duration'] for r in v['cases']],
    'actual_background_identity_jobs':v['actual_background_identity_jobs'],'identity_warmups':4,
    'counter_observation_ticks_including_history':v['counter_observation_ticks_with_history'],'counter_paths':12,
    'pause_windows_verified':v['pause_windows_verified'],'all_actual_O8_raws_exact_to_same_model_full_video':True,
    'all_runtime_photos_inputs_features_and_reject_decisions_reconstructed':True,
    'new_model_input_quantization_256_codes_rechecked':True,'input_quantization_recheck_after_launch_disclosed':True,
    'photo_contact_sheets_actually_viewed':visual['contact_sheets_actually_viewed'],'actual_photo_panels_viewed':visual['actually_viewed_photo_panels'],
    'both_real_networks_run_on_same_PYNQ':True,'same_source_repeats_are_independent_farm_sessions':False,
    'real_camera_or_RFID_hardware':False,'new_permanent_identity_accuracy_proven':False,
    'parent_and_four_identity_workers_terminal_absent':True,'known_O8_and_SSH_Jupyter_read_after_experiment':True,
    'prior_deployed_candidate_replaced':False,'new_training_updates':0,'new_independent_test':False,'whole_goal_complete':False,
    'documents':documents,'local_links_checked':links,'evidence_hashes':{name:sha(ROOT/name) for name in evidence}}
f=ROOT/'results/final_review.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['documents','evidence_hashes']}))
