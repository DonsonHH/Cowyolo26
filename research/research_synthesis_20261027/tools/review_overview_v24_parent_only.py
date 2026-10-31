from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prior_path=ROOT/'results/overview_review_20261031_v23_workload.json';prior=load(prior_path)
assert prior['complete_current_review_coverage']
snapshot=ROOT/'snapshots/overview_v23_before_parent_only_candidate/研究阶段总结_20261030.md'
assert sha(snapshot)==prior['document']['sha256']
entry_path=ROOT/'results/entrypoint_update_20261031_v24_parent_only.json';entry=load(entry_path)
for row in entry['previous_files_and_snapshots']:assert sha(Path(row['snapshot']))==row['sha256']
for row in entry['current_entrypoints']+entry['new_documents']+entry['new_review_sources']:assert sha(Path(row['path']))==row['sha256']
assert sha(Path(entry['diff']['path']))==entry['diff']['sha256']
probe_root=PROJECT/'pynq_startup_probe_20261031';trial_root=PROJECT/'pynq_parent_only_workload_20261031'
probe_path=probe_root/'results/final_review_v1.json';trial_path=trial_root/'results/final_review_v1.json'
probe,trial=load(probe_path),load(trial_path)
assert probe['actual_ARM_identity_warmups']==4 and not probe['original_40s_timeout_reproduced']
assert trial['all8_complete']and trial['actual_counts']==[10,10,10,10,9,10,10,10]
assert trial['all_actual_board_image_forwards']==3187 and trial['actual_timed_O8_forwards']==3115
assert trial['full_association_ticks']==17379 and trial['drop_diagnosis_observation_ticks']==19519
assert not trial['all_offered_200ms_deadlines_met']and not trial['human_total12_consistently_recovered']and not trial['whole_goal_complete']
for root,stage in[(probe_root,probe),(trial_root,trial)]:
 for name,digest in stage['evidence_hashes'].items():assert sha(root/name)==digest
 for row in stage['documents']+stage['reviewed_tools']:assert sha(Path(row['path']))==row['sha256']
main=PROJECT/'研究阶段总结_20261030.md';paper=PROJECT/'paper_readiness_20261030/论文补充_启动开销与完整八轮_20261031.md'
text=main.read_text(encoding='utf-8');paper_text=paper.read_text(encoding='utf-8')
assert '### 3.16 'in text and '双负载约4.90–4.94FPS'in text
v=load(trial_root/'results/independent_verification.json')
for case in v['cases']:
 row=f"| {case['run']} | {int(case['input_producer'])}/{int(case['identity_workload'])} | {case['processed_frames']} | {case['skipped_slots']} | {case['deadline_misses']} | {case['processed_per_second_over_offered_duration']:.3f} | {case['P95_release_to_count_ms']:.2f} | {case['source_down_count']} |"
 assert row in text and row in paper_text
for phrase in['3187','启动探针另计4','19519观察／18路径','低分帧预先就绪','未恢复人工12','C11仍缺真实输入']:
 assert phrase in paper_text,phrase
links=[]
for doc in[main,paper]:
 for match in re.finditer(r'\]\((?:<([^>]+)>|([^\)]+))\)',doc.read_text(encoding='utf-8')):
  target=unquote((match[1]or match[2]).strip())
  if target.startswith(('http://','https://','#')):continue
  path=Path(target);path=path if path.is_absolute()else doc.parent/path;assert path.exists(),target;links.append(str(path))
records=list(prior['current_numeric_record_files'])
for path in[probe_path,trial_path,trial_root/'results/independent_verification.json',trial_root/'results/dropped_frame_counterfactual_verification.json']:
 records.append({'path':str(path),'sha256':sha(path)})
for row in records:assert sha(Path(row['path']))==row['sha256']
value=dict(prior)
value.update({'status':'CURRENT_OVERVIEW_V24_STARTUP4_AND_COMPLETE_PARENT_ONLY8_WITH_RAW_BACKFILL_BOUNDARIES_REVIEWED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'document':{'path':str(main),'sha256':sha(main)},
 'previous_review_preserved':prior_path.name,'previous_complete_manual_read_provenance':prior_path.name,
 'previous_overview_snapshot':{'path':str(snapshot),'sha256':sha(snapshot)},
 'entrypoint_update_evidence':{'path':str(entry_path),'sha256':sha(entry_path)},'changed_text_evidence':entry['diff'],
 'current_numeric_record_files':records,'local_overview_and_new_supplement_links_checked':len(links),
 'review_method':'V23 retained sections match snapshot; all unique V24 changes, both actual reports and new paper supplement read; numeric rows, raw vectors, complete references and actual PNG checked.',
 'manual_review_topics':prior['manual_review_topics']+[
  'Four startup probes with identical stationary foreground; only six import statements differ; no original40s repro',
  'Child PSS decrease64.3MiB is not combined saving; sequential parent+child PSS savings37.54/37.87MiB scoped',
  'Complete new8cases fixed40jobs; D4.936/4.898FPS P95 323.42/339.72ms and counts10/9 retained',
  '3115timed+8qualification16warm+40identity8warm=3187; separate startup4; no CPU neural forwards',
  '17379 actual-association ticks16 paths and19519 exploratory-backfill ticks18paths separated',
  'All eight single missing frame backfills tested; only9515 recovers model reference10, not human12',
  'Same boot different overlay/cache/swap initial state; no full old-new causal speed claim',
  'Original failure and v3 manuscript unchanged; C10,C11,C12 and genuine data/5FPS remain pending'],
 'historical_failed_workload_trial':prior.get('workload_trial'),
 'workload_trial':{'status':'ALL8_COMPLETE_WITH_REMAINING_GAPS','actual_counts':trial['actual_counts'],'board_image_forwards':3187,'full5FPS_proven':False},
 'startup_probe_reviewed':True,'new_board_image_forwards_this_followup':3191,'new_CPU_model_forwards_this_followup':0,
 'current_workload_timing_complete_balanced_repetitions':True,
 'paper_workload_supplement':{'path':str(paper),'sha256':sha(paper),'numeric_rows_verified':8,'C11_status':'pending'},
 'new_benchmark_explicitly_loaded_existing_O8':False,'current_board_loaded_O8_verified_now':True,
 'current_board_O8_verification_scope':'Existing O8 reused for startup probe and parent-only8; final readonly device registers/services checked. Earlier failed-trial explicit programming retains its own scope.',
 'full_periodic_5FPS_target_fixed':False,'paper_ready_for_submission':False,'main_paper_contribution_verified':False,'whole_goal_complete':False})
with(ROOT/'results/overview_review_20261031_v24_parent_only.json').open('x',encoding='utf-8')as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'status':value['status'],'links':len(links),'bound_records':len(records),'new_board_image_forwards':3191,'whole_goal_complete':False}))
