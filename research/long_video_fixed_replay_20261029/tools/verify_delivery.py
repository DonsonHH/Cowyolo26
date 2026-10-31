"""Safely retrieve experiment files and independently recompute native counts."""
from pathlib import Path, PurePosixPath
from collections import defaultdict
import csv, hashlib, json, sys, tarfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
sys.path.insert(0, str(ROOT / 'input'))
from zone_counter import ZoneCounter
from confirmation_counter import ConfirmationHandoffCounter

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, v):
    assert not p.exists(), p
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

def batch_events(observations, admit_prior):
    """Find stable region runs per ID, independently of either production class."""
    samples = defaultdict(dict); first_confirmation = {}; accepted = []
    for index, row in enumerate(observations):
        for tid in row['confirmed_IDs']: first_confirmation.setdefault(int(tid), index)
        for tid, position in row['confirmed_positions'].items(): samples[int(tid)][index] = position
    if admit_prior:
        for tid, index in first_confirmation.items():
            if not index: continue
            previous = observations[index-1]
            if str(tid) not in previous['tentative_positions']: continue
            position = previous['tentative_positions'][str(tid)]
            assert observations[index]['time_s'] - previous['time_s'] <= 2
            samples[tid][index-1] = position
            accepted.append({'track_id': tid, 'observation_time_s': previous['time_s'],
                             'confirmation_time_s': observations[index]['time_s'], 'axis_position': position})
    events = []
    for tid, positions in samples.items():
        origin = None; previous_index = None; region_run = []
        for index, position in sorted(positions.items()):
            row = observations[index]
            if previous_index is not None:
                if index != previous_index + 1: region_run = []
                if row['time_s'] - observations[previous_index]['time_s'] > 2:
                    origin = None; region_run = []
            region = 'A' if position < .4 else ('B' if position > .6 else None)
            if region is None: region_run = []
            else:
                if region_run and region_run[-1] != region: region_run = []
                region_run.append(region)
                if len(region_run) >= 3 and origin != region:
                    if origin is not None:
                        assert str(tid) in row['confirmed_positions']
                        events.append({'time_s': row['time_s'], 'track_id': tid,
                                       'direction': origin + '->' + region, 'frame0': row['frame0']})
                    origin = region
            previous_index = index
    order = {r['frame0']: {int(t): n for n, t in enumerate(r['confirmed_positions'])} for r in observations}
    events.sort(key=lambda e: (e['frame0'], order[e['frame0']][e['track_id']]))
    accepted.sort(key=lambda e: (e['confirmation_time_s'], e['track_id']))
    return events, accepted

def verify_model(spec, p):
    folder = ROOT / 'delivery/results' / spec['name']; summary = load(folder/'summary.json')
    assert summary['checkpoint_sha256'] == spec['sha256']
    assert summary['source_sha256'] == p['source_sha256'] and summary['protocol_sha256'] == sha(ROOT/'protocol/replay_v1.json')
    assert summary['source_frames_read'] == 10125 and summary['model_forwards'] == 2025
    assert summary['formal_reference_scores_computed'] is False and summary['new_training_updates'] == 0
    def read_csv(name):
        with (folder/name).open(encoding='utf-8', newline='') as f: return list(csv.DictReader(f))
    raw = read_csv('raw_detector_boxes.csv'); post = read_csv('post_tracker_boxes.csv'); tracks = read_csv('tracks.csv')
    by_raw = defaultdict(list); by_post = defaultdict(list); by_tracks = defaultdict(list); inverse_error = 0.
    for r in raw:
        frame = int(r['frame']); assert frame in range(0,10125,5)
        u1,v1,u2,v2 = (float(r[k]) for k in ['u1','v1','u2','v2'])
        expected = [v1, 1440-u2, v2, 1440-u1]
        actual = [float(r[k]) for k in ['x1','y1','x2','y2']]
        error = max(abs(a-b) for a,b in zip(expected,actual)); assert error <= .0005
        assert -.001 <= actual[0] <= actual[2] <= 2560.001 and -.001 <= actual[1] <= actual[3] <= 1440.001
        assert .2 - 1e-6 <= float(r['confidence']) <= 1
        inverse_error = max(inverse_error,error); by_raw[frame].append(r)
    for rows, dest in [(post,by_post),(tracks,by_tracks)]:
        for r in rows:
            frame = int(r['frame0']); assert frame in range(0,10125,5) and float(r['time_s']) == frame/25
            dest[frame].append(r)
    seams = load(folder/'seam_checks.json'); observations = load(folder/'observations.json')
    assert [r['frame'] for r in seams] == [r['frame0'] for r in observations] == list(range(0,10125,5))
    baseline = ZoneCounter(**p['counter']); handoff = ConfirmationHandoffCounter(**p['counter'])
    actual_paths = [[],[]]; accepted = []; total_centers = 0
    for seam, row in zip(seams, observations):
        frame = row['frame0']; assert row['time_s'] == frame/25
        assert seam['raw_boxes'] == len(by_raw[frame]) and seam['restored_before_tracker'] is True
        assert [seam[k] for k in ['native_W','native_H','crop_left','crop_right']] == [2560,1440,0,2560]
        assert seam['inverse_rounding_error'] <= .0005
        positions = {}; active = set(); selected = []
        for r in by_post[frame]:
            if not r['track_id']: continue
            tid = int(r['track_id']); active.add(tid)
            if .34 < (float(r['x1'])+float(r['x2']))/5120 < .75:
                cy = (float(r['y1'])+float(r['y2']))/2880
                positions[tid] = cy; selected.append(r)
        assert active == set(row['confirmed_IDs'])
        assert positions == {int(k):v for k,v in row['confirmed_positions'].items()}
        assert len(selected) == len(by_tracks[frame])
        for a,b in zip(selected,by_tracks[frame]):
            assert all(a[k] == b[k] for k in a) and float(b['axis_position']) == positions[int(a['track_id'])]
            total_centers += 1
        tentative = {int(k):v for k,v in row['tentative_positions'].items()}
        outputs = [baseline.update(frame/25,positions), handoff.update(frame/25,positions,tentative,active)]
        for dest, generated in zip(actual_paths, outputs):
            for event in generated: event['frame0'] = frame; dest.append(event)
        assert handoff.last_acceptances == row['accepted_history']; accepted.extend(row['accepted_history'])
    all_events = [load(folder/'confirmed_only_events_all_history.json'),load(folder/'handoff_events_all_history.json')]
    for path, stored, admit in zip(actual_paths, all_events,[False,True]):
        independent, admissions = batch_events(observations,admit)
        assert path == stored == independent
        if admit: assert sorted(accepted,key=lambda e:(e['confirmation_time_s'],e['track_id'])) == admissions
    assert len(raw) == summary['raw_rows_all_history'] and len(tracks) == summary['tracked_ROI_rows_all_history'] == total_centers
    assert inverse_error == summary['maximum_inverse_error'] == max(s['inverse_rounding_error'] for s in seams)
    scopes = []
    for window, scope in zip(p['windows'], summary['all_scope_events']):
        a,b = window['start_frame0'],window['end_frame0_exclusive']; assert scope['source_frame_range_halfopen'] == [a,b]
        for counter,stored in zip(['confirmed_only','confirmation_handoff'],all_events):
            chosen = [e for e in stored if a<=e['frame0']<b]
            assert chosen == load(folder/window['name']/(counter+'_events.json'))
            item = next(c for c in scope['counter_paths'] if c['counter'] == counter)
            assert item['events'] == chosen
            assert item['predicted_down'] == sum(e['direction']=='A->B' for e in chosen)
            assert item['predicted_up'] == sum(e['direction']=='B->A' for e in chosen)
        selected_raw = [r for f,rs in by_raw.items() if a<=f<b for r in rs]
        selected_tracks = [r for f,rs in by_tracks.items() if a<=f<b for r in rs]
        assert scope['sampled_ticks'] == len(range(a,b,5))
        assert scope['raw_rows'] == len(selected_raw)
        assert scope['raw_any_box_ticks'] == len({int(r['frame']) for r in selected_raw})
        assert scope['raw_ROI_ticks'] == len({int(r['frame']) for r in selected_raw if .34<(float(r['x1'])+float(r['x2']))/5120<.75})
        assert scope['tracked_ROI_rows'] == len(selected_tracks)
        assert scope['tracked_ROI_ticks'] == len({int(r['frame0']) for r in selected_tracks})
        assert scope['ROI_track_IDs'] == sorted({int(r['track_id']) for r in selected_tracks})
        scopes.append({'window':window['name'],'counter_paths':scope['counter_paths']})
    return {'model':spec['name'],'observation_ticks':len(observations),'raw_boxes_inverse_verified':len(raw),
            'native_ROI_centers_verified':total_centers,'inverse_max_error_px':inverse_error,
            'accepted_tentative_observations':len(accepted),'counter_paths_independently_recomputed':2,'scopes':scopes}

def main():
    record = load(ROOT/'evidence/delivery_record.json'); archive = ROOT/'replay_delivery.tar.gz'; dest = ROOT/'delivery'
    assert archive.stat().st_size == record['archive_bytes'] and sha(archive) == record['archive_sha256']
    assert not dest.exists()
    with tarfile.open(archive,'r:gz') as tf:
        manifest_data = tf.extractfile('delivery_manifest.json').read(); rows = json.loads(manifest_data)['files']
        expected = {r['file']:r for r in rows}; members = tf.getmembers()
        assert len(expected) == len(rows) and len(members) == record['files'] == len(rows)+1
        assert {m.name for m in members} == set(expected)|{'delivery_manifest.json'}
        for m in members:
            name = PurePosixPath(m.name)
            assert m.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in m.name
            target = dest.joinpath(*name.parts).resolve(); assert target.is_relative_to(dest.resolve())
            data = tf.extractfile(m).read()
            if m.name in expected:
                row = expected[m.name]; assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
            target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(data)
            assert sha(target) == hashlib.sha256(data).hexdigest()
    p = load(ROOT/'protocol/replay_v1.json')
    assert sha(dest/'protocol/replay_v1.json') == sha(ROOT/'protocol/replay_v1.json') == '90bac31ca2224544a1ca62c3a7046842c1c744b584e976d1a4b745d1c9b4bd0a'
    for name,digest in p['input_module_sha256'].items(): assert sha(dest/'input'/name) == sha(ROOT/'input'/name) == digest
    checks = [verify_model(spec,p) for spec in p['models']]
    summary = load(dest/'results/summary.json')
    assert summary['model_forwards'] == sum(x['observation_ticks'] for x in checks) == 8100 and summary['counter_paths'] == 8
    assert summary['models'] == [load(dest/'results'/s['name']/'summary.json') for s in p['models']]
    assert sha(PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json') == p['current_confirmed12_candidate_sha256']
    assert sha(PROJECT/'event_timing_refinement_20261029/reference/assistant_event_timing_v2.json') == p['timing_draft_sha256']
    report = {'status':'DELIVERY_HASH_NATIVE_RESTORATION_EIGHT_COUNTER_PATHS_INDEPENDENTLY_VERIFIED',
              'archive_sha256':sha(archive),'manifest_files':len(rows),'observation_ticks':8100,
              'native_ROI_centers':sum(x['native_ROI_centers_verified'] for x in checks),'checks':checks,
              'formal_reference_scores_computed':False,'whole_goal_complete':False}
    save(ROOT/'results/independent_verification.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='checks'}))
if __name__ == '__main__': main()
