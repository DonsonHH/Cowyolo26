"""Exploratory raw-only backfills; no neural or device inference."""
from pathlib import Path
from datetime import datetime, timezone
import gzip, hashlib, json, os, socket, sys
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname() != 'mu01'
load = lambda path: json.loads(path.read_text())
gz = lambda path: json.loads(gzip.decompress(path.read_bytes()))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
plan = load(ROOT / 'tracker_input/protocol.json')
for row in plan['files']:
    assert sha(ROOT / row['file']) == row['sha256']
sys.path.insert(0, str(ROOT / 'tracker_input/source'))
from frame_pipeline import FramePipeline


def decode(raw):
    boxes = raw[raw[:, 4] >= .2].copy()
    gain = 192 / 1440
    px = round((192 - 1440 * gain) / 2 - .1)
    py = round((192 - 1050 * gain) / 2 - .1)
    boxes[:, [0, 2]] = (boxes[:, [0, 2]] - px) / gain
    boxes[:, [1, 3]] = (boxes[:, [1, 3]] - py) / gain
    boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, 1440)
    boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, 1050)
    return [{'xyxy': [float(value[1]) + 870, 1440 - float(value[2]), float(value[3]) + 870, 1440 - float(value[0])],
             'confidence': float(value[4]), 'class': 0} for value in boxes]


full_case = next(row for row in plan['cases'] if row['run'] == 'r1_A')
drop_case = next(row for row in plan['cases'] if row['run'] == 'r5_D')
with np.load(ROOT / full_case['raw']) as archive:
    full_frames = list(map(int, archive['frame0']))
    full_raw = archive['raw'].copy()
with np.load(ROOT / drop_case['raw']) as archive:
    drop_frames = list(map(int, archive['frame0']))
    drop_raw = archive['raw'].copy()
assert full_frames == list(range(8915, 10874, 5)) and len(drop_frames) == 384
bank = dict(zip(full_frames, full_raw))
for frame, raw in zip(drop_frames, drop_raw):
    assert bank[frame].tobytes() == raw.tobytes()
missing = sorted(set(full_frames) - set(drop_frames))
assert missing == [9020, 9155, 9360, 9385, 9490, 9515, 9720, 10105]
base_trace = gz(ROOT / 'results/tracker_replay/r5_D_actual_trace.json.gz')
full_trace = gz(ROOT / 'results/tracker_replay/r1_A_actual_trace.json.gz')
history = gz(ROOT / 'tracker_input/history.json.gz')


def events(trace):
    return [row for row in trace['handoff_events'] if 8912 <= row['frame0'] <= 10873]


def replay(frames):
    pipeline = FramePipeline(plan['video'], plan['tracker_config'], plan['counter_kwargs'])
    trace = {key: [] for key in ['observations', 'post_tracker', 'confirmed_only_events', 'handoff_events']}
    inputs = [(row['frame0'], row['predictions']) for row in history] + [(frame, decode(bank[frame])) for frame in frames]
    for frame, predictions in inputs:
        result = pipeline.update(frame, predictions)
        trace['observations'].append(result['observation'])
        for key in trace:
            if key != 'observations':
                trace[key].extend(result[key])
    return json.loads(json.dumps(trace))


out = ROOT / 'results/dropped_frame_counterfactual'
out.mkdir(exist_ok=False)
reports = []
variants = [('add_f' + str(frame), [frame]) for frame in missing] + [('add_all_missing', missing)]
for name, restored in variants:
    frames = sorted(set(drop_frames) | set(restored))
    actual = replay(frames)
    if len(restored) == 1:
        for key in actual:
            assert [row for row in actual[key] if row['frame0'] < restored[0]] == [row for row in base_trace[key] if row['frame0'] < restored[0]]
    else:
        assert actual == full_trace
    trace_path = out / (name + '.json.gz')
    with gzip.GzipFile(filename=str(trace_path), mode='wb', mtime=0) as stream:
        stream.write(json.dumps(actual, separators=(',', ':')).encode())
    scoped = events(actual)
    reports.append({'variant': name, 'restored_frames': restored, 'scheduled_frames': frames,
                    'observations': len(actual['observations']), 'trace_file': trace_path.relative_to(ROOT).as_posix(),
                    'trace_sha256': sha(trace_path), 'down_count': sum(row['direction'] == 'A->B' for row in scoped),
                    'up_count': sum(row['direction'] == 'B->A' for row in scoped), 'events': scoped,
                    'prefix_before_single_restored_frame_exact': len(restored) == 1,
                    'all_restored_trace_matches_complete_r1_A': len(restored) == 8})
assert 'torch' not in sys.modules
summary = {'status': 'ALL8_SINGLE_FRAME_AND_ALL_MISSING_RAW_ONLY_POSTHOC_BACKFILLS_COMPLETE',
           'created_UTC': datetime.now(timezone.utc).isoformat(), 'Slurm_job_id': os.environ['SLURM_JOB_ID'],
           'source_full_raw_sha256': sha(ROOT / full_case['raw']), 'source_dropped_raw_sha256': sha(ROOT / drop_case['raw']),
           'source_full_down_count': sum(row['direction'] == 'A->B' for row in events(full_trace)),
           'baseline_dropped_down_count': sum(row['direction'] == 'A->B' for row in events(base_trace)),
           'missing_frames': missing, 'reports': reports, 'counter_paths': 18,
           'observation_ticks': sum(row['observations'] for row in reports), 'new_model_forwards': 0,
           'posthoc_exploratory_same_previously_seen_source': True, 'independent_human_event_GT': False,
           'device_scheduler_changed_or_5FPS_retested': False, 'whole_goal_complete': False}
with (out / 'summary.json').open('x') as stream:
    json.dump(summary, stream, indent=2)
    stream.write('\n')
print(json.dumps({key: value for key, value in summary.items() if key != 'reports'}), flush=True)
