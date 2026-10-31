"""Reuse the full eight-case audit, correct its old boundary assumption."""
from pathlib import Path
from datetime import datetime, timezone
import ast, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent / 'pynq_workload_ablation_20261031'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
records = []


def derive(name, replacements=(), source_name=None):
    source_path = BASE / 'tools' / (source_name or name)
    text = source_path.read_text(encoding='utf-8')
    for old, new, count in replacements:
        assert text.count(old) == count, (name, old, text.count(old), count)
        text = text.replace(old, new)
    destination = ROOT / 'tools' / name
    if name.endswith('.py'):
        ast.parse(text)
    with destination.open('x', encoding='utf-8') as stream:
        stream.write(text)
    records.append({'source': str(source_path), 'source_sha256': sha(source_path),
                    'destination': str(destination), 'destination_sha256': sha(destination)})


old_sha = '9329f1fc27a2059ffbddd459b289b69061d9f05f4f51e1e1ca840e5528456cb8'
new_sha = '7e2d82a5d6af9d67414544fd896b3c7cf73095d43304f097c12ecd48ddddd97a'
derive('verify_archive.py')
source = (BASE / 'tools/verify_results.py').read_text(encoding='utf-8')
start = source.index('# Inherited fields from the four-run source protocol')
end = source.index('result = {', start)
old_notes = source[start:end]
derive('verify_results.py', [
    ('protocol/run_v2.json', 'protocol/run_v1.json', 1),
    (old_sha, new_sha, 1),
    ("ROOT / 'payload_v2'", "ROOT / 'payload_v1'", 1),
    ("assert before['sample_monotonic_ns'] <= epoch < case['period_end_monotonic_ns'] <= after['sample_monotonic_ns']",
     "assert before['sample_monotonic_ns'] < after['sample_monotonic_ns']\n    assert epoch < case['period_end_monotonic_ns'] <= after['sample_monotonic_ns']", 1),
    ("'process_major_faults_delta': after['ru_majflt'] - before['ru_majflt'],",
     "'process_major_faults_delta': after['ru_majflt'] - before['ru_majflt'],\n                  'resource_before_sample_minus_period_start_ms': (before['sample_monotonic_ns'] - epoch) / 1e6,\n                  'resource_after_sample_minus_period_end_ms': (after['sample_monotonic_ns'] - case['period_end_monotonic_ns']) / 1e6,", 1),
    (old_notes, "# Fresh protocol contains only its operative eight-run budget fields.\nprotocol_notes = []\n", 1),
    ('ALL8_SAVED_RAW_TIMING_EVENTS_PRODUCER_FIXED40_IDENTITY_AND_RESOURCE_COUNTERS_VERIFIED_WITH_DISCLOSED_PROTOCOL_METADATA_INCONSISTENCY',
     'ALL8_PARENT_ONLY_IMPORT_WORKLOAD_SAVED_RAW_TIMING_EVENTS_PRODUCER_FIXED40_IDENTITY_AND_RESOURCE_COUNTERS_VERIFIED', 1),
])
derive('collect_results.py', [
    ('cow_research_workload_ablation_20261031', 'cow_research_parent_only_workload_20261031', 1),
    (old_sha, new_sha, 1),
    ("ROOT/'launch.json',ROOT/'run.log',ROOT/'final_state.json'", "ROOT/'launch.json',ROOT/'run.log',ROOT/'final_state.json',ROOT/'preflight.json'", 1),
])
for name in ['launch_collection.sh', 'collection_status.sh']:
    derive(name, [('cow_research_workload_ablation_20261031', 'cow_research_parent_only_workload_20261031', 1)])
derive('prepare_tracker_replay.py', [
    ('protocol/run_v2.json', 'protocol/run_v1.json', 2),
    ('pynq_workload_ablation_20261031', 'pynq_parent_only_workload_20261031', 1),
    ('cow-workload-track', 'cow-parent-track', 1),
])
derive('verify_tracker_reference.py', [('cow-workload-track', 'cow-parent-track', 1)])
derive('plot_results.py')
derive('server_preflight.sh')
with (ROOT / 'evidence/verification_tools_preparation.json').open('x', encoding='utf-8') as stream:
    json.dump({'created_UTC': datetime.now(timezone.utc).isoformat(), 'records': records,
               'new_model_forwards': 0, 'resource_sampling_boundaries_read_as_recorded_not_assumed_atomic': True}, stream, indent=2)
    stream.write('\n')
print(json.dumps({'tools_prepared': len(records), 'new_model_forwards': 0}))
