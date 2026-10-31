"""Audit every CPU replay trace against the saved ARM association trace."""
from pathlib import Path
from datetime import datetime, timezone
import gzip, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / 'reference_delivery'
BOARD = ROOT / 'delivery'
load = lambda path: json.loads(path.read_text(encoding='utf-8'))
gz = lambda path: json.loads(gzip.decompress(path.read_bytes()))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
summary = load(REF / 'results/tracker_replay/summary.json')
assert summary['status'] == 'ALL5_FULL_TRACKER_ASSOCIATION_AND_EVENT_REPLAYS_MATCH_ACTUAL_ARM_WITH_FROZEN_TOLERANCES'
assert summary['new_model_forwards'] == 0 and not summary['Torch_imported']
assert summary['host'] != 'mu01'
job = summary['Slurm_job_id']
assert job == (REF / 'tracker_job_id.txt').read_text().strip()
assert f'{job}|cow-workload-track|COMPLETED|0:0|' in (REF / 'logs/tracker_sacct.txt').read_text()
assert not (REF / f'logs/tracker-{job}.err').read_text().strip()
assert sha(REF / 'tracker_input/protocol.json') == sha(ROOT / 'tracker_input/protocol.json')
plan = load(REF / 'tracker_input/protocol.json')
for row in plan['files']:
    assert sha(REF / row['file']) == sha(ROOT / row['file']) == row['sha256']
assert plan['source_board_protocol_sha256'] == sha(BOARD / 'run_protocol.json')
reports = []
total_ticks = total_boxes = 0
for case, reported in zip(plan['cases'], summary['reports']):
    actual = gz(REF / 'results/tracker_replay' / (case['run'] + '_actual_trace.json.gz'))
    expected = gz(BOARD / 'results' / case['run'] / 'counter_trace.json.gz')
    assert case['run'] == reported['run'] and reported['IDs_and_events_exact']
    assert actual['confirmed_only_events'] == expected['confirmed_only_events']
    assert actual['handoff_events'] == expected['handoff_events']
    assert len(actual['observations']) == len(expected['observations']) == reported['observation_ticks']
    assert len(actual['post_tracker']) == len(expected['post_tracker']) == reported['post_tracker_rows']
    max_box = max_axis = 0.
    for left, right in zip(actual['post_tracker'], expected['post_tracker']):
        assert all(left[key] == right[key] for key in ['frame0', 'time_s', 'track_id', 'confidence'])
        delta = max(abs(a - b) for a, b in zip(left['xyxy'], right['xyxy']))
        assert delta <= plan['box_tolerance_pixels']
        max_box = max(max_box, delta)
    for left, right in zip(actual['observations'], expected['observations']):
        assert all(left[key] == right[key] for key in ['frame0', 'time_s', 'confirmed_IDs'])
        for field in ['confirmed_positions', 'tentative_positions']:
            assert left[field].keys() == right[field].keys()
            for key in left[field]:
                delta = abs(left[field][key] - right[field][key])
                assert delta <= plan['axis_tolerance']
                max_axis = max(max_axis, delta)
        assert len(left['accepted_history']) == len(right['accepted_history'])
        for a, b in zip(left['accepted_history'], right['accepted_history']):
            assert all(a[key] == b[key] for key in ['track_id', 'observation_time_s', 'confirmation_time_s'])
            delta = abs(a['axis_position'] - b['axis_position'])
            assert delta <= plan['axis_tolerance']
            max_axis = max(max_axis, delta)
    assert max_box == reported['maximum_box_difference'] and max_axis == reported['maximum_axis_difference']
    total_ticks += len(actual['observations'])
    total_boxes += len(actual['post_tracker'])
    reports.append({'run': case['run'], 'maximum_box_difference': max_box, 'maximum_axis_difference': max_axis,
                    'observation_ticks': len(actual['observations']), 'post_tracker_rows': len(actual['post_tracker']),
                    'IDs_and_events_exact': True})
assert len(reports) == len(summary['reports']) == 5
assert total_ticks == summary['observation_ticks'] and total_boxes == summary['post_tracker_rows']
assert summary['counter_paths'] == 10
result = {'status': 'FAILED_EIGHT_RUN_PLAN_ALL5_COMPLETED_ASSOCIATIONS_AND10_EVENT_PATHS_CPU_REPLAY_VERIFIED',
          'created_UTC': datetime.now(timezone.utc).isoformat(), 'Slurm_job_id': job,
          'observation_ticks': total_ticks, 'post_tracker_rows': total_boxes, 'counter_paths': 10,
          'reports': reports, 'new_model_forwards': 0, 'whole_goal_complete': False}
with (ROOT / 'results/tracker_reference_verification.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps({key: value for key, value in result.items() if key != 'reports'}))
