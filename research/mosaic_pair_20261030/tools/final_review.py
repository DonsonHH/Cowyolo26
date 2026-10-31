from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
s=load(ROOT/'delivery/results/evaluation_v2/summary.json');v=load(ROOT/'results/independent_verification.json')
m=load(ROOT/'results/media_verification.json');visual=load(ROOT/'results/visual_review.json')
candidate=load(ROOT/'results/retained_candidate.json');controls=load(ROOT/'delivery/results/control_weight_reproduction.json')
labels=load(ROOT/'results/source_labels_post_training_integrity.json')
assert s['actual_source_image_forwards']==25350 and v['training_batch_rows_checked']==12780 and v['gradient_gate_record_rows_checked']==7350
assert v['actual_training_image_presentations']==408540 and s['counter_paths']==36
orig=[r['down'] for r in s['video_metrics'] if r['scene']=='original' and r['counter']=='handoff_events']
t5=[r['formal_event_metrics']['TP'] for r in s['video_metrics'] if r['scene']=='toros' and r['counter']=='handoff_events' and r['stride']==6]
t30=[r['formal_event_metrics']['TP'] for r in s['video_metrics'] if r['scene']=='toros' and r['counter']=='handoff_events' and r['stride']==1]
assert orig==[10,10,10,10,10,11] and t5==[1,3,1,3,0,0] and t30==[1,4,3,4,1,1]
assert all(r['up']==0 for r in s['video_metrics'] if r['scene']=='original')
assert all(r['formal_event_metrics']['FP']==0 for r in s['video_metrics'] if r['scene']=='toros' and r['counter']=='handoff_events')
assert [r['TP'] for r in s['validation_metrics']]==[1819,1838,1810,1813,1851,1831]
assert [r['unmatched_prediction'] for r in s['validation_metrics']]==[587,230,526,443,414,212]
assert controls['all3_state_dicts_exact'] and all(r['state_tensors_byte_value_exact']==r['state_tensors']==708 for r in controls['rows'])
assert candidate['name']=='mosaic050_seed26' and not candidate['new_model_quantized_or_O8_executed'] and not candidate['prior_deployed_candidate_replaced']
assert labels['label_counts']=={'train':6809,'val':1571} and labels['changed']==[]
assert m['strict_decoded_video_frames']==1962 and m['SVG_bars']==30 and visual['figures_actually_viewed']==5 and visual['panels_actually_viewed']==12
for row in visual['files']:assert row['actually_viewed'] and sha(row['path'])==row['sha256']
execution=load(ROOT/'protocol/formal_execution_v1.json')
for path,digest in execution['files_sha256'].items():assert sha(ROOT/path)==digest,path
execution=load(ROOT/'protocol/evaluation_execution_v2.json')
for path,digest in execution['files_sha256'].items():assert sha(ROOT/path)==digest,path
evidence=['protocol/training_v1.json','protocol/preflight_execution_v1.json','protocol/formal_execution_v1.json','protocol/evaluation_v1.json',
    'protocol/evaluation_execution_v1.json','protocol/evaluation_v2.json','protocol/evaluation_execution_v2.json','protocol/media_v1.json',
    'results/transfer_verification.json','results/independent_verification.json','results/media_verification.json','results/visual_review.json','results/retained_candidate.json',
    'results/source_labels_post_training_integrity.json','results/regression_diagnostic.json','results/all_six_checkpoints_frozen.json',
    'delivery/results/control_weight_reproduction.json','delivery/results/evaluation_v2/summary.json','delivery/results/evaluation_v2/counter_regression_gate.json',
    'evidence/collection.txt','evidence/evaluation_status01.txt','evidence/results_status01.txt','evidence/post_training_source_read.txt',
    'results/media_extraction_diagnostic.json','tools/preflight.py','tools/train_condition.py','tools/evaluate.py','tools/evaluate_v2.py',
    'tools/verify_results.py','tools/verify_media.py','tools/render_media.py']
documents=[];links=0
for name in ['计划与验收.md','配对训练结果与量化候选.md','Review与当前状态.md']:
    file=ROOT/name;text=file.read_text(encoding='utf-8');assert '\ufffd' not in text
    for match in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',text):
        target=unquote(match[1] or match[2])
        if re.match(r'^[A-Za-z]:[/\\]',target):assert Path(target).exists();links+=1
    documents.append({'path':str(file.resolve()),'sha256':sha(file),'lines_read_and_reviewed':len(text.splitlines())})
r={'status':'SIX_PAIRED_TRAININGS25350_REPLAYS36_EVENT_PATHS_AND12_VISUAL_PANELS_REVIEWED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'formal_training_runs':6,'formal_training_updates':7350,'discarded_smoke_updates':4,
    'persisted_training_batch_rows':12780,'persisted_gradient_gate_rows':7350,'training_image_presentations':408540,
    'raw_full_gradient_arrays_saved':False,'paired_rotation_and_optimizer_schedules_exact':3,'all3_mosaic100_state_dicts_reproduced':True,
    'reproduced_parameter_and_buffer_tensors':2124,'post_training_source_label_files_unchanged':8380,
    'actual_evaluation_source_image_forwards':25350,'actual_inference_hook_image_calls':25350,'old_baseline_traces_exact':9,
    'validation_matching_problems':9426,'counter_observation_ticks':16404,'counter_paths':36,'publisher_temporal_matching_paths':24,'NN_anchor_hashes_checked':48,
    'original_counts_by_condition_order':orig,'Toros5Hz_TP_by_condition_order':t5,'Toros30Hz_TP_by_condition_order':t30,
    'validation_TP_by_condition_order':[1819,1838,1810,1813,1851,1831],
    'validation_unmatched_prediction_by_condition_order':[587,230,526,443,414,212],
    'primary_retained_for_quantization':'mosaic050_seed26','primary_checkpoint_sha256':candidate['checkpoint_sha256'],
    'new_candidate_quantized_or_executed_on_board':False,'prior_deployed_candidate_replaced':False,
    'first_failed_evaluation_new_source_forwards':0,'strict_regression_metadata_repair_only':True,
    'all6_training_main_jobs_completed':True,'all_training_stderr_clean':False,'pin_memory_exception_headers_after_complete_record':2,
    'pin_memory_exception_root_cause_confirmed':False,'all_launched_phase_jobs_terminal':True,
    'strict_decoded_video_frames':1962,'SVG_bars_checked':30,'figures_actually_viewed':5,'panels_actually_viewed':12,
    'weight_freeze_zero_forward_field_scope':'post_training_unified_evaluation_only;training_epoch_validation_and_internal_shape_probes_excluded',
    'new_independent_test':False,'actual_board_actions':0,'whole_goal_complete':False,'local_links_checked':links,
    'evidence_hashes':{p:sha(ROOT/p) for p in evidence},'documents':documents}
target=ROOT/'results/final_review.json';assert not target.exists();target.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k not in ['evidence_hashes','documents']}))
