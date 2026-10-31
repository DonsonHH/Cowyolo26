from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
v=load(ROOT/'results/independent_verification.json');p=load(ROOT/'protocol/run_v1.json')
assert v['actual_ARM_measured_forwards']==180 and v['actual_ARM_warmup_forwards']==4 and v['actual_ARM_network_calls']==184
assert v['experiment_status']=='BOTH90_ENCODERS180_ARM_FEATURES_AND480_FIXED_DECISIONS_PASS'
assert[v[k]for k in['numeric_failed_images','Top1_changes','Top5_order_changes','decision_changes']]==[0,0,0,0]
assert[[r[k]for k in['known_Top1','C','W','U','unknown_FA']]for r in v['primary_outcomes']]==[[22,10,2,18,3],[30,3,0,27,0]]
assert load(ROOT/'evidence/binary_upload_terminal.json')['tty_restored_verified']and load(ROOT/'evidence/original_results_v1_terminal.json')['tty_restored_verified']
post=load(ROOT/'evidence/board_post_archive_final_state.json');assert post['exit_code']==0 and'FINAL20_ARM_ALL_OWN_PIDS_ABSENT_BOUND_MODELS_O8_LOCK_SERVICES_VERIFIED'in post['output']
for row in load(ROOT/'delivery/result_manifest.json'):assert sha(ROOT/'delivery'/row['file'])==row['sha256']
for row in p['payload_files']:assert sha(ROOT/'payload'/row['file'])==row['sha256']
report=ROOT/'同90图ARM实机一致性与计时范围.md';links=[]
for match in re.finditer(r'\]\((?:<([^>]+)>|([^\)]+))\)',report.read_text()):
 target=unquote((match[1]or match[2]).strip());path=Path(target);path=path if path.is_absolute()else report.parent/path;assert path.exists(),target;links.append(str(path))
files=[ROOT/'计划与验收.md',report,ROOT/'delivery/result_manifest.json',ROOT/'delivery/results/record.json',ROOT/'delivery/final_board_state.json']+[f for folder in['tools','protocol','evidence','results']for f in(ROOT/folder).rglob('*')if f.is_file()and'__pycache__'not in f.parts]
result=dict(v);result.update({'status':'BOTH90_REAL_ARM_ENCODERS180_VECTORS480_DECISIONS_COMPLETE_ORIGINALS_TIMING_AND_DEFAULT_PRESERVATION_REVIEWED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'all_raw_vectors_source_and_scores_verified':True,'same90_CPU_evaluation_not_new_independent_test':True,'thresholds_not_changed_for_hardware':True,'primary_Top1_C_W_U_FA':[[22,10,2,18,3],[30,3,0,27,0]],'new_heldout_date_pixels_opened':False,'default_O8_encoder_tracker_or_reject_threshold_changed':False,
 'new_CPU_reference_forwards':0,'new_training_updates':0,'new_PL_forwards':0,'all_own_experiment_and_collection_PIDs_confirmed_absent':True,'external_network_recovered':False,'whole_goal_complete':False,
 'report_read_fully_and_manual_scope_review_completed':True,'assistant_self_review_not_independent_human':True,'local_report_links_checked':len(links),'report_sha256':sha(report),'evidence_hashes':{f.relative_to(ROOT).as_posix():sha(f)for f in sorted(set(files))}})
target=ROOT/'results/final_review.json';assert not target.exists();target.write_bytes(json.dumps(result,ensure_ascii=False,indent=2).encode()+bytes([10]));print(json.dumps({k:result[k]for k in['status','actual_ARM_network_calls','decision_changes','report_sha256']}))
