"""Freeze transfer/submit/collect commands only after all eight inputs exist."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent / 'pynq_workload_ablation_20261031/tools'
load = lambda path: json.loads(path.read_text(encoding='utf-8'))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
bundle = load(ROOT / 'evidence/tracker_input_bundle.json')
verification = load(ROOT / 'results/independent_verification.json')
assert verification['fixed_photo_tensor_raw_feature_score_jobs_verified'] == 40
records = []
for name in ['initialize_tracker_reference_v1.sh', 'stage_submit_tracker_reference_v1.sh',
             'tracker_reference_status_v1.sh', 'collect_tracker_reference_v1.sh']:
    original = BASE / name
    text = original.read_text(encoding='utf-8')
    assert 'pynq_workload_ablation_20261031' in text
    text = text.replace('pynq_workload_ablation_20261031', 'pynq_parent_only_workload_20261031')
    if name == 'stage_submit_tracker_reference_v1.sh':
        substitutions = [('5880515', str(bundle['bytes'])),
                         ('8299bb9d8ad9e0ff1a7655be07946348e701961c630d2a730be05b21f8c9adfb', bundle['sha256']),
                         ('==26', '==' + str(bundle['members'])),
                         ("len(plan['cases'])==5", "len(plan['cases'])==8"),
                         ('FIVE_ACTUAL_SCHEDULES', 'EIGHT_ACTUAL_SCHEDULES')]
    elif name == 'collect_tracker_reference_v1.sh':
        substitutions = [('cow-workload-track', 'cow-parent-track'),
                         ('ALL5_FULL_TRACKER', 'ALL8_FULL_TRACKER'),
                         ("summary['observation_ticks']==10663", "summary['observation_ticks']==" + str(verification['counter_observation_ticks'])),
                         ("summary['counter_paths']==10", "summary['counter_paths']==16"),
                         ('TERMINAL_FIVE_PERIOD_REFERENCE_AND_FIGURE_ARCHIVE_COMPLETE', 'TERMINAL_EIGHT_PERIOD_REFERENCE_AND_FIGURE_ARCHIVE_COMPLETE')]
    else:
        substitutions = []
    for old, new in substitutions:
        assert text.count(old) == 1, (name, old, text.count(old))
        text = text.replace(old, new)
    path = ROOT / 'tools' / name
    with path.open('xb') as stream:
        stream.write(text.encode())
    records.append({'source': str(original), 'source_sha256': sha(original), 'file': str(path), 'sha256': sha(path)})
with (ROOT / 'evidence/reference_operations_frozen.json').open('x', encoding='utf-8') as stream:
    json.dump({'created_UTC': datetime.now(timezone.utc).isoformat(), 'records': records, 'new_model_forwards': 0}, stream, indent=2)
    stream.write('\n')
print(json.dumps({'status': 'EIGHT_PERIOD_CPU_REFERENCE_OPERATIONS_FROZEN', 'bundle_bytes': bundle['bytes'],
                  'expected_association_ticks': verification['counter_observation_ticks'], 'new_model_forwards': 0}))
