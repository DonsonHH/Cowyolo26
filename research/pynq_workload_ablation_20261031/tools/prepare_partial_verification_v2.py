"""Correct a verifier assumption; preserve the original data and failed v1."""
from pathlib import Path
from datetime import datetime, timezone
import ast, hashlib, json

root = Path(__file__).resolve().parents[1]
prior = root / 'tools/verify_partial_results_v1.py'
source = prior.read_text(encoding='utf-8')
before = "assert before['sample_monotonic_ns'] <= epoch < case['period_end_monotonic_ns'] <= after['sample_monotonic_ns']"
after = "assert before['sample_monotonic_ns'] < after['sample_monotonic_ns']\n    assert epoch < case['period_end_monotonic_ns'] <= after['sample_monotonic_ns']"
assert source.count(before) == 1
source = source.replace(before, after)
before = "'process_major_faults_delta': after['ru_majflt'] - before['ru_majflt'],"
after = before + "\n                  'resource_before_sample_minus_period_start_ms': (before['sample_monotonic_ns'] - epoch) / 1e6,\n                  'resource_after_sample_minus_period_end_ms': (after['sample_monotonic_ns'] - case['period_end_monotonic_ns']) / 1e6,"
assert source.count(before) == 1
source = source.replace(before, after)
before = "'protocol_metadata_notes': protocol_notes, 'cases': cases,"
after = "'resource_counter_window_scope': 'Logged resource snapshots are not atomic period boundaries; r5 starts 37.018878ms after its offer clock. Deltas describe the sampled windows, not an exact whole-period attribution.',\n          " + before
assert source.count(before) == 1
source = source.replace(before, after)
ast.parse(source)
with (root / 'tools/verify_partial_results_v2.py').open('x', encoding='utf-8') as stream:
    stream.write(source)
result = {'created_UTC': datetime.now(timezone.utc).isoformat(),
          'status': 'VERIFIER_V1_ASSUMED_COUNTER_SNAPSHOT_PRECEDED_OFFER_CLOCK_CORRECTED_IN_V2',
          'v1_sha256': hashlib.sha256(prior.read_bytes()).hexdigest(),
          'failed_v1_line': 253,
          'failure': 'AssertionError: before sample <= period start is not guaranteed by the executable measurement code',
          'observed_r5_before_minus_start_ms': 37.018878,
          'correction': 'Check actual timestamp ordering and retain per-run sample offsets; do not call the counter delta an atomic full-period measurement.',
          'model_results_or_protocol_modified': False, 'new_model_forwards': 0}
with (root / 'evidence/verification_v1_failure_and_v2_correction.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print('V1 preserved; V2 records actual resource sample windows; no models run.')
