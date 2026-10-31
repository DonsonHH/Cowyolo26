from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
p=load(ROOT/'protocol/run_v1.json');v=load(ROOT/'results/partial_observation_v1.json')
assert [r['source_down_count']for r in v['observed_complete_case_summaries']]==[10,10,8]
for c in v['observed_complete_case_summaries']:
 assert c['processed_frames']+c['skipped_slots']==392
 assert abs(c['processed_per_second_over_offered_duration']-c['processed_frames']/78.4)<1e-12
assert sum(c['processed_frames']for c in v['observed_complete_case_summaries'])+350==1451
for row in v['evidence_files']:assert sha(ROOT/row['file'])==row['sha256']
for row in p['payload_files']:assert sha(ROOT/'payload'/row['file'])==row['sha256']
for path in(ROOT/'tools').glob('*.py'):ast.parse(path.read_text())
report=ROOT/'实际触发对照_部分观察与恢复.md';links=[]
for match in re.finditer(r'\]\((.*?)\)',report.read_text()):
 target=match.group(1).strip('<>');assert(report.parent/target).exists(),target;links.append(target)
assert not(ROOT/'delivery').exists()
assert not(ROOT/'results/independent_verification.json').exists()
assert not(ROOT/'results/reference_independent_verification.json').exists()
files=[ROOT/'计划与验收.md',report]
for folder in['tools','protocol','evidence','results']:
 files.extend(f for f in(ROOT/folder).rglob('*')if f.is_file()and'__pycache__'not in f.parts)
record={'status':'PARTIAL_TRIGGER_OBSERVATIONS_COUNTS_ARITHMETIC_HASHES_AND_RECOVERY_LIMITS_REVIEWED_NOT_FULL_EXPERIMENT_VERIFICATION',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'observed_case_counts':[10,10,8],'observed_complete_case_summaries':3,
 'fourth_run_processed_lower_bound':350,'timed_O8_calls_observed_lower_bound':1451,'raw_outputs_or_photos_received':False,
 'fourth_case_terminal_received':False,'full_numeric_counter_or_identity_verification_complete':False,'source_original_experiment_restarted':False,
 'user_confirmed_power_or_connection_change':True,'new_model_forwards_by_review':0,'recovery_code_AST_checked':True,
 'recovery_code_executed_on_board':False,'cold_boot_ID_and_current_PL_not_conflated_in_recovery_code':True,
 'original_model_or_PL_reprogrammed_for_access_recovery':False,'report_read_fully_and_claim_boundaries_reviewed':True,
 'assistant_self_review_not_independent_human':True,'whole_goal_complete':False,'report_sha256':sha(report),'local_links_checked':len(links),
 'evidence_hashes':{f.relative_to(ROOT).as_posix():sha(f)for f in sorted(set(files))}}
out=ROOT/'results/interruption_review_v1.json';assert not out.exists();out.write_bytes(json.dumps(record,ensure_ascii=False,indent=2).encode()+bytes([10]))
print(json.dumps({k:record[k]for k in['status','observed_case_counts','raw_outputs_or_photos_received','fourth_case_terminal_received','whole_goal_complete']}))
