"""Independent event arithmetic for all exploratory raw-only backfill traces."""
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone
import gzip, hashlib, importlib.util, json, sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
REF = ROOT / 'reference_delivery'
load = lambda path: json.loads(path.read_text(encoding='utf-8'))
gz = lambda path: json.loads(gzip.decompress(path.read_bytes()))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
module_path = PROJECT / 'long_video_fixed_replay_20261029/tools/verify_delivery.py'
spec = importlib.util.spec_from_file_location('backfill_event_scanner', module_path)
scanner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = scanner
spec.loader.exec_module(scanner)
summary = load(REF / 'results/dropped_frame_counterfactual/summary.json')
tracker = load(ROOT / 'results/tracker_reference_verification.json')
assert summary['Slurm_job_id'] == tracker['Slurm_job_id']
assert summary['status'] == 'ALL8_SINGLE_FRAME_AND_ALL_MISSING_RAW_ONLY_POSTHOC_BACKFILLS_COMPLETE'
assert summary['new_model_forwards'] == 0 and not summary['device_scheduler_changed_or_5FPS_retested']
assert summary['baseline_dropped_down_count'] == 9 and summary['source_full_down_count'] == 10
full = REF / 'tracker_input/r1_A/actual_raw.npz'
dropped = REF / 'tracker_input/r5_D/actual_raw.npz'
assert sha(full) == summary['source_full_raw_sha256'] and sha(dropped) == summary['source_dropped_raw_sha256']
with np.load(full) as archive:
    full_frames = list(map(int, archive['frame0']))
    bank = dict(zip(full_frames, archive['raw'].copy()))
with np.load(dropped) as archive:
    baseline_frames = list(map(int, archive['frame0']))
    for frame, raw in zip(baseline_frames, archive['raw']):
        assert bank[int(frame)].tobytes() == raw.tobytes()
missing = sorted(set(full_frames) - set(baseline_frames))
assert missing == summary['missing_frames'] == [9020, 9155, 9360, 9385, 9490, 9515, 9720, 10105]
base = gz(REF / 'results/tracker_replay/r5_D_actual_trace.json.gz')
complete = gz(REF / 'results/tracker_replay/r1_A_actual_trace.json.gz')
ticks = paths = 0
reports = []
for index, row in enumerate(summary['reports']):
    restored = [missing[index]] if index < 8 else missing
    assert row['restored_frames'] == restored
    frames = sorted(set(baseline_frames) | set(restored))
    assert frames == row['scheduled_frames']
    path = REF / row['trace_file']
    assert sha(path) == row['trace_sha256']
    trace = gz(path)
    assert [item['frame0'] for item in trace['observations']] == list(range(0, 8915, 5)) + frames
    assert len(trace['observations']) == row['observations']
    if len(restored) == 1:
        for key in trace:
            assert [item for item in trace[key] if item['frame0'] < restored[0]] == [item for item in base[key] if item['frame0'] < restored[0]]
    else:
        assert trace == complete and row['all_restored_trace_matches_complete_r1_A']
    tracked = defaultdict(list)
    for item in trace['post_tracker']:
        tracked[item['frame0']].append(item)
    for observation in trace['observations']:
        positions, ids = {}, set()
        for item in tracked[observation['frame0']]:
            tid = item['track_id']
            if tid is None:
                continue
            ids.add(tid)
            x1, y1, x2, y2 = item['xyxy']
            if .34 < (x1 + x2) / (2 * 2560) < .75:
                positions[str(tid)] = (y1 + y2) / (2 * 1440)
        assert observation['confirmed_positions'] == positions and observation['confirmed_IDs'] == sorted(ids)
    for key, handoff in [('confirmed_only_events', False), ('handoff_events', True)]:
        events, _ = scanner.batch_events(trace['observations'], handoff)
        assert events == trace[key]
        paths += 1
        if handoff:
            events = [event for event in events if 8912 <= event['frame0'] <= 10873]
            assert events == row['events']
            assert sum(event['direction'] == 'A->B' for event in events) == row['down_count']
            assert sum(event['direction'] == 'B->A' for event in events) == row['up_count']
    ticks += len(trace['observations'])
    reports.append({'variant': row['variant'], 'restored_frames': restored,
                    'down_count': row['down_count'], 'up_count': row['up_count'],
                    'difference_from_dropped_baseline9': row['down_count'] - 9})
assert len(reports) == 9 and ticks == summary['observation_ticks'] == 19519 and paths == summary['counter_paths'] == 18
result = {'status': 'ALL9_POSTHOC_RAW_BACKFILL_TRACES18_EVENT_PATHS_AND19519_OBSERVATIONS_VERIFIED',
          'created_UTC': datetime.now(timezone.utc).isoformat(), 'Slurm_job_id': tracker['Slurm_job_id'],
          'missing_frames': missing, 'baseline_down_count': 9, 'complete_input_down_count': 10,
          'reports': reports, 'observation_ticks': ticks, 'counter_paths': paths,
          'new_model_forwards': 0, 'same_previously_seen_source': True,
          'independent_event_or_permanent_identity_GT': False, 'on_device_implementation_or_5FPS_improvement_proven': False,
          'whole_goal_complete': False}
with (ROOT / 'results/dropped_frame_counterfactual_verification.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result))
