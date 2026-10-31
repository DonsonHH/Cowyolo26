"""Scientific invariants: bounded availability, mutation isolation, ID isolation."""
from causal_selector import CausalSelector
import json

def row(tid, xyxy):
    return {'track_id': tid, 'xyxy': xyxy}

s = CausalSelector()
past = row(1, [1000, 100, 1400, 600]); s.observe(0, [past])
past['xyxy'][0] = 99999  # Caller mutation must not change observed evidence.
s.observe(5, [row(1, [1000, 1000, 1400, 1440]), row(2, [1000, 100, 1400, 600])])
first = s.choose(5, 1)
assert first['selected']['frame0'] == 0 and first['selected']['xyxy'][0] == 1000
snapshot = json.dumps(first, sort_keys=True)
s.observe(10, [row(1, [900, 30, 1880, 1300])])
assert json.dumps(first, sort_keys=True) == snapshot  # Future availability cannot rewrite prior job.
try:
    s.choose(5, 1)
    raise AssertionError('Past call after future observation accepted')
except AssertionError as error:
    assert str(error) != 'Past call after future observation accepted'
s.observe(35, [row(1, [1000, 1000, 1400, 1440])])
assert all(c['frame0'] >= 10 for c in s.choose(35, 1)['candidates'])
for f in [40, 45, 50, 55, 60, 65, 70]:
    s.observe(f, [row(1, [1000, 100, 1400, 600])])
result = s.choose(70, 1)
assert len(s.frames) == 6 and result['selected']['frame0'] == 70
assert all(c['track_id'] == 1 and 45 <= c['frame0'] <= 70 for c in result['candidates'])
print(json.dumps({'status': 'CAUSALITY_AVAILABILITY_STALENESS_ID_AND_MUTATION_INVARIANTS_PASS', 'external_data_read': False, 'new_model_forwards': 0}))
