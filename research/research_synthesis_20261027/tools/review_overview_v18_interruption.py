from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re,difflib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_bytes(json.dumps(v,ensure_ascii=False,indent=2).encode()+bytes([10]))

old=load(ROOT/'results/overview_review_20261030_v17.json');main=PROJECT/'研究阶段总结_20261030.md'
snapshot=ROOT/'snapshots/overview_v17_before_trigger_access_interruption/研究阶段总结_20261030.md';assert sha(snapshot)==old['document']['sha256']
assert old['entire_current_overview_read_in_full']
records=list(old['current_numeric_record_files'])
for row in records:assert sha(Path(row['path']))==row['sha256']
p=PROJECT/'identity_trigger_pair_20261030/results/interruption_review_v1.json';records.append({'path':str(p),'sha256':sha(p)})
partial=load(p);assert partial['observed_case_counts']==[10,10,8]and partial['fourth_case_terminal_received']is False
links=[]
for match in re.finditer(r'\]\((?:<([^>]+)>|([^\)]+))\)',main.read_text()):
 target=unquote((match[1]or match[2]).strip())
 if target.startswith(('http://','https://','#')):continue
 p=Path(target);p=p if p.is_absolute()else main.parent/p;assert p.exists(),target;links.append(str(p))
entry=ROOT/'results/entrypoint_update_20261030_v18_interruption.json'
for row in load(entry)['current_entrypoints']:assert sha(Path(row['path']))==row['sha256']
before=snapshot.read_text().splitlines();after=main.read_text().splitlines();diff=list(difflib.unified_diff(before,after,fromfile='verified_v17',tofile='current_v18',n=3))
diff_file=ROOT/'results/overview_diff_20261030_v18_interruption.txt';assert not diff_file.exists();diff_file.write_bytes(chr(10).join(diff).encode()+bytes([10]))
value={'status':'CURRENT_OVERVIEW_V18_REVIEWED_PARTIAL_TRIGGER_EVIDENCE_ACCESS_CHANGE_AND_NO_FALSE_COMPLETION_CLAIM',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'document':{'path':str(main),'sha256':sha(main)},
 'reviewer_kind':'assistant_self_review_not_independent_human','complete_current_review_coverage':True,
 'review_method':'Previous complete manual read of hash-matched V17 retained sections, plus manual review of every V18 changed passage and source interruption report; new raw-result verification explicitly absent.',
 'previous_complete_manual_read_provenance':'overview_review_20261030_v17.json','all_changed_text_read_and_claim_checked':True,
 'manual_review_topics':['Three host summaries10,10,8 vs unreceived fourth terminal','Fourth350and1451timed calls are lower bounds, not stage totals','No local raw/trace/photo/vector or final event verification','User-reported power or connection movement, exact time unknown','COM6zero-output plus knownIPtimeouts do not prove completion/failure/data loss','DHCP192.168.3.13 observed, no IP/proxy/routing changes','Recovery first reads source protocol/bootID; no new model/PL/O8 program','Same-boot live original task never replaced, cold-boot PID identity not conflated','Partial-stage code prepared != runtime verification passed','Previous completed CPU/ARM/scientific evidence retained at its original time scope'],
 'current_numeric_record_files':records,'local_overview_links_checked':len(links),'previous_review_preserved':'overview_review_20261030_v17.json',
 'previous_overview_snapshot':{'path':str(snapshot.resolve()),'sha256':sha(snapshot)},
 'entrypoint_update_evidence':{'path':str(entry.resolve()),'sha256':sha(entry)},
 'changed_text_evidence':{'path':str(diff_file.resolve()),'sha256':sha(diff_file)},
 'new_model_forwards':None,'exact_current_trigger_stage_forward_total_unverified':True,'observed_timed_O8_call_lower_bound':1451,
 'new_model_forwards_by_offline_recovery_review':0,'new_training_updates':0,'actual_trigger_stage_finalized':False,
 'original_experiment_PID':10099,'original_experiment_current_process_state':'unknown_after_user_reported_access_change',
 'fourth_case_terminal_received':False,'actual_trigger_stage_raw_or_photo_vectors_received':False,
 'actual_trigger_stage_full_independent_verification_completed':False,'recovery_code_executed_on_board':False,
 'original_experiment_restarted':False,'user_confirmed_power_or_connection_change':True,'current_board_carrier_live_rechecked':False,
 'current_board_loaded_O8_verified_now':False,'prior_same90_ARM_consistency_completed':True,
 'source_results_lost_claimed':False,'network_configuration_changed':False,'independent_event_JSON_received':False,
 'current_event_permanent_ID_mapping_received':False,'reliable_automatic_identity_recovery_proven':False,
 'live_camera_RFID_proven':False,'full_periodic_5FPS_target_fixed':False,'reservedMar05toMar11_pixels_opened':False,
 'main_paper_contribution_verified':False,'whole_goal_complete':False}
save(ROOT/'results/overview_review_20261030_v18_interruption.json',value)
print(json.dumps({'status':value['status'],'main_local_links':len(links),'bound_numeric_records':len(records),'current_main_sha256':sha(main),'new_raw_results_verified':False}))
