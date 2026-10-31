from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
ROOT = Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
target = ROOT / 'results/optimizer_final_review.json'
assert not target.exists()
synthesis = ROOT.parent / 'research_synthesis_20261027/results/review_after_optimizer_control.json'
record = json.loads(synthesis.read_text(encoding='utf-8'))
assert len(record['documents']) == 20
for row in record['documents']: assert sha(Path(row['path'])) == row['sha256']
study = record['actual_optimizer_causal_controls_inspected']
assert study['single_QLinearAdd_restoration_causal_control_passed'] is True
paths = ['图优化残差加法定位与下一步.md', '图优化Review.md',
         'protocol/optimizer_probe_v1.json', 'protocol/optimizer_isolation_v1.json',
         'results/optimizer_local_verification.json', 'results/optimizer_delivery_status_01.txt',
         'optimizer_delivery/results/optimizer_probe/summary.json',
         'optimizer_delivery/results/optimizer_isolation/summary.json',
         'optimizer_delivery/results/optimizer_independent_verification.json']
output = {'status': 'OPTIMIZER_CAUSAL_CONTROL_AND_FULL_REPORT_REVIEW_COMPLETE',
          'created_UTC': datetime.now(timezone.utc).isoformat(), 'goal_turn_classification': 'progress',
          'full_manual_report_review_complete': True, 'actual_results': study,
          'synthesis_review_sha256': sha(synthesis),
          'files': [{'path': p, 'sha256': sha(ROOT / p)} for p in paths],
          'formal_QAT_updates': 0, 'all_seeds_training_or_FPGA_verified': False,
          'remaining_goal_requirements': ['independent_real_bidirectional_events', 'identity_RF_mapping_and_calibration',
                                          'trainable_multi_seed_numeric_gate', 'PYNQ_Z2_joint_inference',
                                          'principal_contribution_and_publication_evidence'],
          'whole_goal_complete': False}
target.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'status': output['status'], 'documents': len(record['documents']),
                  'links': record['local_links_checked'], 'whole_goal_complete': False}))
