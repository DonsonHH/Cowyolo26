from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
ROOT = Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
target = ROOT/'results/final_review.json'
assert not target.exists()
combined_path = ROOT.parent/'research_synthesis_20261027/results/review_after_evaluation_intake.json'
combined = json.loads(combined_path.read_text(encoding='utf-8'))
assert len(combined['documents']) == 31
for row in combined['documents']: assert sha(Path(row['path'])) == row['sha256']
actual = combined['actual_independent_evaluation_intake_preparation_inspected']
assert actual['catalog_conditions'] == 17 and actual['intake_tests'] == 16
assert actual['same_external_input_gap_evidenced_by_three_prior_goal_audits'] is True
paths = ['README.md','Review与当前状态.md','results/required_input_audit.json',
         'results/preparation_verification.json','results/frozen_prediction_catalog.json',
         'results/annotation_jump_before_fix.json','results/annotation_jump_fix.json',
         'results/annotation_browser_retest.json','results/annotation_jump_fixed.png',
         'results/known_QA_intake_check.json','results/existing_public_annotation_inventory.json','results/intake_test_results.json',
         'results/intake_test_results_v2.json','results/live_compute_audit.txt',
         'tools/catalog.py','tools/inspect_annotation.py','tools/test_intake.py',
         'tools/test_intake_before_utf8_child.py']
record = {'status':'EVALUATION_INTAKE_AND_UI_FIX_PREPARATION_FULL_REVIEW_COMPLETE',
          'created_UTC':datetime.now(timezone.utc).isoformat(),
          'previous_goal_turn_classification':'progress','current_goal_turn_classification':'progress',
          'phase_preparation_and_full_manual_review_complete':True,
          'actual_results':actual,'synthesis_review_sha256':sha(combined_path),
          'evidence_files':[{'path':p,'sha256':sha(ROOT/p)} for p in paths],
          'completion_audit_result':'Originalgoal remainsunproven; independenttruthandactualboard informationrequired.',
          'blocked_audit':{'same_input_gap_recurred_at_least_three_consecutive_goal_turns':True,
                           'recurrence_evidence':'results/required_input_audit.json',
                           'necessary_available_preparation_completed':True,
                           'remaining_original_next_steps_require_external_inputs':True,
                           'more_seen_devset_training_not_a_substitute_for_required_evaluation':True},
          'new_reference_received':False,'source_accuracy_certified':False,
          'FPGA_execution_verified':False,'whole_goal_complete':False}
target.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'status':record['status'],'documents':31,'local_links':combined['local_links_checked'],
                  'original_goal_complete':False,'remaining_next_steps_require_user_inputs':True}))
