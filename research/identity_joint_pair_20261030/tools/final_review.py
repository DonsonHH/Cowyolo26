from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re

ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
v=load(ROOT/'results/independent_verification.json');tracker=load(ROOT/'tracker_delivery/results/tracker_replay/summary.json')
assert tracker['status']=='ALL4_FULL_TRACKER_ASSOCIATION_AND_EVENT_REPLAYS_MATCH_ACTUAL_ARM_WITH_FROZEN_TOLERANCES'
assert tracker['observation_ticks']==v['counter_observation_ticks']and tracker['counter_paths']==8
assert[v['actual_timed_O8_forwards'],v['actual_ARM_total_forwards'],v['all_new_actual_board_forwards']]==[1564,85,1665]
assert[v['cases'][i]['processed_frames']for i in range(4)]==[392,390,390,392]
assert[c['source_down_count']for c in v['cases']]==[10,10,10,10]and[c['deadline_misses']for c in v['cases']]==[80,69,67,76]
assert[c['accepted_predictions']for c in v['cases']]==[1,0,0,1]
assert load(ROOT/'evidence/pair_original_v1_terminal.json')['tty_restored_verified']
post=load(ROOT/'evidence/board_post_archive_final_state.json');assert post['exit_code']==0 and'PAIR_PARENT_CHILDREN_COLLECTOR_ABSENT_O8_DEFAULT_ENCODER_AND_LOCK_SERVICES_VERIFIED'in post['output']
visual=load(ROOT/'results/candidate_panel_review.json');assert visual['panels_actually_viewed']==5 and visual['unique_photos']==10
report=ROOT/'新旧身份模型固定负载同板对照.md';links=[]
for text in re.findall(r'\]\(([^)]+)\)',report.read_text()):assert(report.parent/text).exists(),text;links.append(text)
for row in load(ROOT/'board_delivery/result_manifest.json'):assert sha(ROOT/'board_delivery'/row['file'])==row['sha256']
files=[p for folder in['protocol','evidence','tools','results']for p in(ROOT/folder).rglob('*')if p.is_file()and'__pycache__'not in p.parts]+[report,ROOT/'计划与验收.md',ROOT/'board_delivery/result_manifest.json',ROOT/'reference_delivery/result_manifest.json',ROOT/'tracker_delivery/result_manifest.json',ROOT/'tracker_delivery/results/tracker_replay/summary.json']
result=dict(v);result.update({'status':'FOUR_PAIRED_OLD_NEW_NEW_OLD_REAL_BOARD_RUNS_ALL_ORIGINALS40_PHOTOS_AND_FULL_ASSOCIATION_REPLAY_REVIEWED','created_UTC':datetime.now(timezone.utc).isoformat(),'tracker_replay_job_id':tracker['Slurm_job_id'],'tracker_replay_all4_full_associations_pass':True,'all_new_model_forwards_in_this_stage':1745,'current_event_identity_correctness_proven':False,'default_encoder_O8_tracker_or_threshold_replaced':False,'same10_photos_not40_independent_cows_disclosed':True,'source_gallery_after_event_and_same_source_development_disclosed':True,'all_parent_child_collection_PIDs_confirmed_absent':True,'full_original_board_archive_verified':True,'all5_candidate_panels_actually_viewed':True,'assistant_manual_report_read_and_claim_review_completed':True,'assistant_self_review_not_independent_human':True,'local_report_links_checked':len(links),'report_sha256':sha(report),'evidence_hashes':{p.relative_to(ROOT).as_posix():sha(p)for p in sorted(set(files))},'whole_goal_complete':False})
target=ROOT/'results/final_review.json';assert not target.exists();target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in['status','actual_timed_O8_forwards','actual_ARM_total_forwards','all_new_model_forwards_in_this_stage','tracker_replay_job_id','report_sha256']}))
