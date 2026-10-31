"""Counterfactual operating points on frozen scores, never applied thresholds."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
ROOT = Path(__file__).resolve().parents[1]
rows_path = ROOT / 'results/per_query660.json'
protocol_path = ROOT / 'protocol/matched_coverage_v1.json'
assert not protocol_path.exists()
protocol = {'name': 'Frozen-score matchedcorrectacceptance coverage diagnostic v1',
            'created_UTC': datetime.now(timezone.utc).isoformat(),
            'perquery_sha256': hashlib.sha256(rows_path.read_bytes()).hexdigest(),
            'fixed_target': 'Eachseed ownpairedfloat frozen correctacceptedC, notchosen fromQATscores',
            'calculation': 'Among existingQATbestscore thresholds attaining at leasttargetC, choosehighestthreshold; monotonicacceptance minimizes falseaccepts at that coverage. ReportW andunknownfalseaccepts.',
            'scope': 'Labelusing counterfactual on reuseddevelopmentqueries, no adoptedthreshold, retraining ornewperformanceclaim.',
            'original_thresholds_or_predictions_modified': False, 'whole_goal_complete': False}
protocol_path.write_text(json.dumps(protocol, indent=2), encoding='utf-8')
rows = json.loads(rows_path.read_text(encoding='utf-8'))
results = []
for seed in [26, 27, 28]:
    baseline = [r for r in rows if r['seed'] == seed and r['condition'] == 'paired_float_continuation']
    qat = [r for r in rows if r['seed'] == seed and r['condition'] == 'integer_forward_qat']
    target = sum(r['outcome'] == 'C' for r in baseline)
    candidates = []
    for threshold in sorted({r['top1_score'] for r in qat}, reverse=True):
        accepted = [r for r in qat if r['top1_score'] >= threshold]
        C = sum(r['known'] and r['rank_correct'] for r in accepted)
        if C < target: continue
        candidates.append({'seed': seed, 'target_float_C': target, 'hypothetical_QAT_threshold': threshold,
            'C': C, 'W': sum(r['known'] and not r['rank_correct'] for r in accepted),
            'U': 25 - sum(r['known'] for r in accepted),
            'unknown_false_accepts': sum(not r['known'] for r in accepted),
            'threshold_applied_to_real_predictions': False})
    assert candidates
    result = candidates[0]
    assert all(r['unknown_false_accepts'] >= result['unknown_false_accepts'] and r['W'] >= result['W'] for r in candidates)
    results.append(result)
output = {'status': 'THREE_LABEL_USING_MATCHED_COVERAGE_OPERATING_POINTS_COMPUTED',
          'protocol_sha256': hashlib.sha256(protocol_path.read_bytes()).hexdigest(), 'results': results,
          'original_thresholds_or_predictions_modified': False, 'independent_test_accuracy': None,
          'whole_goal_complete': False}
target = ROOT / 'results/matched_coverage.json'
assert not target.exists()
target.write_text(json.dumps(output, indent=2), encoding='utf-8')
print(json.dumps(output))
