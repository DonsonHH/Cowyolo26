from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
ROOT = Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
target = ROOT / 'results/final_review.json'
assert not target.exists()
synthesis = ROOT.parent / 'research_synthesis_20261027/results/review_after_trainable_integer.json'
record = json.loads(synthesis.read_text(encoding='utf-8'))
assert len(record['documents']) == 22
for row in record['documents']: assert sha(Path(row['path'])) == row['sha256']
actual = record['actual_trainable_integer_smoke_inspected']
assert actual['independent_integer_layers'] == 2496 and actual['files_verified'] == 82
paths = ['三seed可训练整数前向与准入结果.md', 'Review与当前状态.md',
         'protocol/trainable_integer_smoke_v1.json', 'results/local_verification.json',
         'results/initialization_probe.json', 'results/initialization_local_verification.json',
         'results/delivery_status_01.txt', 'results/initialization_status_01.txt',
         'delivery/results/smoke_v2/summary.json', 'delivery/results/independent_verification.json']
result = {'status': 'TRAINABLE_THREE_SEED_SMOKE_DELIVERY_AND_FULL_REPORT_REVIEW_COMPLETE',
          'created_UTC': datetime.now(timezone.utc).isoformat(), 'goal_turn_classification': 'progress',
          'full_manual_report_review_complete': True, 'actual_results': actual,
          'synthesis_review_sha256': sha(synthesis),
          'evidence_files': [{'path': p, 'sha256': sha(ROOT / p)} for p in paths],
          'all_smoke_initial_and_postupdate_gates_verified': True,
          'actual_discarded_smoke_updates': 6, 'formal_QAT_updates_in_this_phase': 0,
          'formal_training_is_separate_stage': 'integer_qat_20261028',
          'remaining_goal_requirements': ['formal_paired_training_and_identity_risk',
            'independent_bidirectional_count', 'identity_RF_mapping', 'PYNQ_Z2_joint_inference', 'principal_paper_contribution'],
          'FPGA_execution_verified': False, 'whole_goal_complete': False}
target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'status': result['status'], 'documents': 22,
                  'links': record['local_links_checked'], 'whole_goal_complete': False}))
