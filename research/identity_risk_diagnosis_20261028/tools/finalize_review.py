from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
ROOT = Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
target = ROOT / 'results/final_review.json'
assert not target.exists()
combined_path = ROOT.parent / 'research_synthesis_20261027/results/review_after_frozen_identity_risk.json'
combined = json.loads(combined_path.read_text(encoding='utf-8'))
assert len(combined['documents']) == 27
for row in combined['documents']: assert sha(Path(row['path'])) == row['sha256']
actual = combined['actual_frozen_identity_risk_diagnosis_inspected']
assert actual['frozen_thresholds_unchanged'] is True and actual['manual_visual_QA'] == 'PASS'
assert actual['matched_coverage_is_label_using_diagnostic_not_adopted_threshold'] is True
paths = ['身份错配拒识与下一步.md', '公开计数候选入口复查.md', 'Review与当前状态.md',
         'protocol/frozen_risk_v1.json', 'protocol/matched_coverage_v1.json',
         'results/summary.json', 'results/independent_verification.json', 'results/matched_coverage.json',
         'results/local_delivery_verification.json', 'results/render_status_01.txt',
         'delivery/results/render_record.json', 'evidence/HF_connector_availability.json']
record = {'status': 'FROZEN_IDENTITY_RISK_DIAGNOSTIC_AND_FULL_REPORT_REVIEW_COMPLETE',
          'created_UTC': datetime.now(timezone.utc).isoformat(),
          'previous_goal_turn_classification': 'progress', 'current_goal_turn_classification': 'progress',
          'phase_deliverables_and_manual_report_review_complete': True, 'actual_results': actual,
          'synthesis_review_sha256': sha(combined_path),
          'evidence_files': [{'path': p, 'sha256': sha(ROOT / p)} for p in paths],
          'public_counting_candidates': {'new_qualified_independent_bidirectional_reference_obtained': False,
              'HF_precomputed_predictions_not_admitted_as_truth': True, 'author_form_submitted': False},
          'new_training_or_inference': False, 'models_and_thresholds_unchanged': True,
          'remaining_original_goal_requirements': [
              {'requirement': 'Independent_real_bidirectional_count_accuracy', 'status': 'incomplete',
               'needed': 'ReviewerJSON and fresh complete direction-labeled events'},
              {'requirement': 'Reliable_identity_RFID_recovery', 'status': 'partial',
               'needed': 'Independent identities/RF mapping and validated chosen risk/coverage'},
              {'requirement': 'PYNQ_Z2_detector_and_background_identity_joint_execution', 'status': 'unverified',
               'needed': 'SSH/image/toolversions, final arithmetic mapping and measured jointboard result'},
              {'requirement': 'Principal_scientific_contribution_and_publication_evidence', 'status': 'not_yet_proven'}],
          'FPGA_execution_verified': False, 'whole_goal_complete': False}
target.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'status': record['status'], 'documents': 27, 'local_links': combined['local_links_checked'],
                  'new_training_or_inference': False, 'whole_goal_complete': False}))
