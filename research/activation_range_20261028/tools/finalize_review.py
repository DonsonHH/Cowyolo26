from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
ROOT = Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
target = ROOT / 'results/final_review.json'
assert not target.exists()
synthesis = ROOT.parent / 'research_synthesis_20261027/results/review_after_activation_range_controls.json'
combined = json.loads(synthesis.read_text(encoding='utf-8'))
assert len(combined['documents']) == 29
for row in combined['documents']: assert sha(Path(row['path'])) == row['sha256']
actual = combined['actual_training_range_clipping_controls_inspected']
assert actual['all12_fixed_weight_unclipping_controls_lower_mean_teacher_cosine'] is True
assert actual['new_training_updates'] == 0 and actual['validation_or_test_reads'] == 0
paths = ['量化范围与截断对照.md', 'Review与当前状态.md', 'protocol/activation_range_v1.json',
         'results/local_verification.json', 'results/conditions36.csv', 'results/local_metric_rounding_probe.json',
         'results/delivery_status_01.txt', 'delivery/results/probe/summary.json',
         'delivery/results/independent_verification.json', 'tools/probe.py', 'tools/independent_verify.py',
         'tools/verify_local_before_metric_tolerance.py', 'tools/verify_local.py']
status = (ROOT / 'results/delivery_status_01.txt').read_text(encoding='utf-8')
for job in ['130003', '130004', '130005']:
    assert any(line.startswith(job + '|') and '|COMPLETED|0:0|' in line for line in status.splitlines())
record = {'status': 'TRAIN_ONLY_RANGE_AND_FIXED_WEIGHT_CLIPPING_PHASE_FULL_REVIEW_COMPLETE',
          'created_UTC': datetime.now(timezone.utc).isoformat(),
          'previous_goal_turn_classification': 'progress', 'current_goal_turn_classification': 'progress',
          'phase_experiment_delivery_and_manual_report_review_complete': True,
          'actual_results': actual, 'synthesis_review_sha256': sha(synthesis),
          'evidence_files': [{'path': path, 'sha256': sha(ROOT / path)} for path in paths],
          'decision': 'Retain originalmodelandthresholds; do notadopt directunclipping. Thisdoesnotevaluate recalibrationthenretraining.',
          'remaining_original_goal_requirements': [
              {'requirement': 'Independent_real_bidirectional_event_accuracy', 'status': 'incomplete',
               'needed': 'Independent reviewerJSON and freshdirection-labeled complete sessions'},
              {'requirement': 'Independent_identity_and_realRFID_recovery', 'status': 'partial',
               'needed': 'Independentidentity/RFmapping andvalidatedrisk/coverage'},
              {'requirement': 'PYNQ_Z2_detector_and_background_identity_joint_inference', 'status': 'unverified',
               'needed': 'User SSH/image/toolversions, finalarithmeticmapping andactualjointboard measurements'},
              {'requirement': 'Principal_publication_contribution', 'status': 'not_yet_proven'}],
          'FPGA_execution_verified': False, 'whole_goal_complete': False}
target.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'status': record['status'], 'documents': 29, 'local_links': combined['local_links_checked'],
                  'new_training_updates': 0, 'whole_goal_complete': False}))
