from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
ROOT = Path(__file__).resolve().parents[1]
summary = json.loads((ROOT / 'results/optimizer_probe_summary.json').read_text())
firsts = json.loads((ROOT / 'results/optimizer_first_divergences.json').read_text())
assert summary['protocol_sha256'] == hashlib.sha256((ROOT / 'protocol/optimizer_probe_v1.json').read_bytes()).hexdigest()
assert summary['prior_OFF_ALL_outputs_exactly_reproduced'] is True
assert summary['levels_passed'] == {'OFF': 8, 'BASIC': 8, 'EXTENDED': 6, 'ALL': 6}
names = [v['first_common_integer_difference']['optimized_producer']['name'] for v in firsts]
assert len(names) == 2 and len(set(names)) == 1
path = ROOT / 'protocol/optimizer_isolation_v1.json'
assert not path.exists()
protocol = {'name': 'Same-input QLinearAdd isolation and one-node graph restoration v1',
    'created_UTC': datetime.now(timezone.utc).isoformat(),
    'serialized_ALL_sha256': summary['snapshots']['ALL']['sha256'],
    'source_candidate_sha256': summary['source_candidate_sha256'], 'target_node': names[0],
    'vectors': list(range(8)), 'data': 'Same8already-used training regression tensors, no newdata',
    'controls': ['Capture identical upstream integerA/B tensors from frozenOFF and serializedALL, embedding unchanged',
                 'Run isolated actualQLinearAdd and originalDQ_Add_Q with exactlysameA/B andscales/zero-points',
                 'Replace onlythe identifiedQLinearAdd in actualserializedALL by fouroriginalstandardops, leaveeveryothernode unchanged',
                 'Separately test documentedALL session.disable_quant_qdq=1, not confounded with single-nodecontrol'],
    'gate': {'max_absolute_error': .001, 'minimum_cosine': .9999},
    'interpretation': 'Causal claim restricted to these8traininginputs and thispinnedmodel/runtime; reportallfailures, no identity/FPGA/generalization claim.',
    'new_training_updates': 0, 'whole_goal_complete': False}
path.write_text(json.dumps(protocol, indent=2), encoding='utf-8')
print(json.dumps({'protocol_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'target_node': names[0]}))
