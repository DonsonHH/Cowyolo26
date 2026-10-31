from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
v=load(ROOT/'results/independent_verification.json');s=load(ROOT/'delivery/results/evaluation/summary.json');freeze=load(ROOT/'delivery/results/all_checkpoints_frozen.json')
assert v['formal_conditions']==15 and v['epochs_completed']==150 and v['formal_optimizer_updates']==18375
assert v['observed_training_batches']==31950 and v['training_image_presentations']==1021350
assert v['validation_image_conditions']==23565 and v['candidate_validation_IoUs']==43792 and v['raw_box_inverse_checks']==61225
assert v['maximum_inverse_error']==0 and v['native_ROI_centers_verified']==10137
assert v['tracker_observation_ticks']==41010 and v['independent_counter_paths']==90 and v['publisher6_event_score_conditions']==60
assert v['cached_control_regression_counter_paths']==36 and v['actual_network_image_forwards_supported']==63375
assert v['per_update_gradient_arrays_recovered'] is False and v['rotation_schedules_are_reconstructed_not_observed'] is True
assert freeze['total_formal_optimizer_updates']==18375 and freeze['discarded_smoke_updates']==12
assert s['actual_detector_source_image_forwards']==s['predictor_hook_image_forwards']==63375
assert s['all_weights_freeze_sha256']==sha(ROOT/'delivery/results/all_checkpoints_frozen.json')
counts=[];matches=[]
for size,rotate in [(192,False),(192,True),(256,False),(256,True),(320,True)]:
    counts.append([next(r['down'] for r in s['video_metrics'] if r['scene']=='original' and r['input_size']==size and r['right_angle']==rotate and r['seed']==seed and r['counter']=='handoff_events') for seed in [26,27,28]])
    matches.append([next(r['matched'] for r in s['validation_metrics'] if r['input_size']==size and r['right_angle']==rotate and r['seed']==seed) for seed in [26,27,28]])
assert counts==[[6,4,5],[6,5,5],[8,9,8],[7,8,8],[7,8,7]]
assert matches==[[1754,1596,1773],[1819,1810,1851],[1697,1730,1800],[1835,1851,1845],[1843,1845,1846]]
assert all(r['up']==0 for r in s['video_metrics'] if r['scene']=='original')
assert all(r['formal_event_metrics'] is None for r in s['video_metrics'] if r['scene']=='original')
for r in freeze['conditions']:
    folder=ROOT/'delivery/results/training'/r['condition']['condition_id']
    assert sha(folder/'weights/last.pt')==r['last_checkpoint_sha256'] and sha(folder/'weights/best.pt')==r['archived_best_sha256']
meta=load(ROOT/'evidence/transfer.json');assert sha(ROOT/'results_delivery.tar.gz')==meta['sha256'] and meta['members']==380 and meta['manifest_files']==379
jobs=(ROOT/'evidence/collect_results.txt').read_text()
for i in range(15):assert '130518_'+str(i)+'|cow-lowres-factorial|FAILED|1:0|' in jobs
assert '130542|cow-factorial-freeze|COMPLETED|0:0|' in jobs and '130544|cow-factorial-eval|COMPLETED|0:0|' in jobs
original=PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json';assert sha(original)=='5536882add54dc5315a3865b01782c5838c5c39adcce1ea984ec8963a7079d9b'
retained={original.relative_to(PROJECT).as_posix():sha(original)};accepted=load(original)
for key,hk in [('reference_path','reference_sha256'),('checkpoint_path','checkpoint_sha256')]:
    file=Path(accepted[key]);assert sha(file)==accepted[hk];retained[file.relative_to(PROJECT).as_posix()]=sha(file)
file=Path(accepted['source_event_record']['events_path']);assert sha(file)==accepted['source_event_record']['events_sha256'] and len(load(file))==12;retained[file.relative_to(PROJECT).as_posix()]=sha(file)
docs=[ROOT/'计划与验收.md',ROOT/'低分辨率训练对照与采用决定.md',ROOT/'Review与当前状态.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
links=[]
for doc in docs:
    text=doc.read_text(encoding='utf-8');assert '\ufffd' not in text
    for match in re.finditer(r'!?\[[^\]]*\]\((?:<([^>]+)>|([^\)]+))\)',text):
        link=match.group(1) or match.group(2)
        if link.startswith(('http://','https://','#')):continue
        file=Path(unquote(link.split('#')[0]));file=file if file.is_absolute() else doc.parent/file
        assert file.exists(),(doc,link);links.append({'document':str(doc.resolve()),'link':link})
evidence=['protocol/training_v4.json','protocol/formal_execution_v1.json','protocol/evaluation_v1.json','protocol/evaluation_runtime_v1.json',
 'results/independent_verification.json','results/transfer_verification.json','results/group_table.json',
 'results/training_metrics.csv','results/validation_metrics.csv','results/video_metrics.csv',
 'delivery/results/all_checkpoints_frozen.json','delivery/input/training_terminal_states.json',
 'delivery/results/evaluation/summary.json','delivery/results/evaluation/cached_control_regression_gate.json',
 'delivery/results/preflight.json','delivery/results/preflight_grad.json','evidence/schedule_diagnosis01.json','evidence/collect_results.txt']
result={'status':'ALL15_LOWRES_TRAINED_WEIGHTS63375_FORWARDS90_COUNTER_PATHS_REVIEWED_WITH_NONADOPTION',
 'created_host_UTC':datetime.now(timezone.utc).isoformat(),'training_and_offline_evaluation_phase_complete':True,'whole_goal_complete':False,
 'new_conditions':15,'historical320_plain_controls':3,'new_total_epochs':150,'formal_optimizer_updates':18375,
 'observed_training_batches':31950,'training_image_presentations':1021350,'discarded_smoke_updates':12,
 'all15_fixed_last_epoch_weights_frozen_before_video':True,'original_training_array_postprocess_states_preserved':'ALL15_FAILED1:0_AT_LF_ONLY_SCHEDULE_HASH_ASSERT',
 'no_training_repeated_after_completed_weights':True,'gradient_arrays_recovered':False,'rotation_schedules_reconstructed_not_observed':True,
 'actual_new_detector_image_forwards':63375,'predictor_hook_image_count':63375,'validation_matching_cases':23565,'candidate_validation_IoUs':43792,
 'native_inverse_boxes':61225,'maximum_native_inverse_error':0,'ROI_centers_verified':10137,'new_tracker_updates':41010,
 'independent_counter_paths':90,'publisher6_event_score_conditions':60,'cached_control_regression_counter_paths':36,
 'new_original_down_counts_groups_by_seeds':counts,'new_validation_matches_groups_by_seeds':matches,
 'all_seeds_and_negative_results_retained':True,'new_model_adopted_globally':False,'all_new_count_conditions_restore12':False,
 'new15_weights_actual_PYNQ_video_count_verified':False,'foreground_background_joint5FPS_proven':False,'new_independent_test':False,
 'original_human12_milestone_preserved':True,'retained_artifact_hashes':retained,'evidence_hashes':{r:sha(ROOT/r) for r in evidence},
 'documents':[{'path':str(d.resolve()),'sha256':sha(d)} for d in docs],'local_links_checked':len(links),
 'manual_numeric_scope_and_nonadoption_decision_review_completed':True,'new_figures_or_videos_generated_in_this_training_phase':0}
file=ROOT/'results/final_review.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['retained_artifact_hashes','evidence_hashes','documents']}))
