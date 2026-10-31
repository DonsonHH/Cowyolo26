"""Bind existing same-scope prediction artifacts; no new model inference."""
from pathlib import Path
from collections import Counter
import csv, hashlib, json
ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
SOURCE_SHA = '5d1d8c197abbebfd98d11b7900fe2655013acc43cf5e01bebc7c72a3bcde95a1'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def normalized(events):
    return sorted([{'source_frame': int(r['source_frame']), 'time_s': float(r['time_s']), 'direction': r['direction']} for r in events],
                  key=lambda r: (r['source_frame'], r['direction']))


def main():
    target = ROOT / 'results/frozen_prediction_catalog.json'
    assert not target.exists()
    stages = [('detector_training_20261027', 'protocol/detector_v1.json'),
              ('composition_control_20261027', 'protocol/composition_v1.json'),
              ('orientation_video_20261027', 'protocol/video_rotation_v1.json')]
    records = []
    for stage, protocol in stages:
        folder = PROJECT / stage
        summary_path = folder / 'delivery/results/inference/summary.json'
        summary = load(summary_path)
        assert summary['protocol_sha256'] == sha(folder / protocol)
        for condition in summary['conditions']:
            scene = next(r for r in condition['scenes'] if r['scene'] == 'source')
            assert scene['source_sha256'] == SOURCE_SHA and scene['source_output_frame_range'] == [8912, 10873]
            assert scene['counter_initialised_at_source_frame'] == 0 and scene['sampled_inference_frames'] == 2175
            file = folder / f'delivery/results/inference/{condition["name"]}/source_events.json'
            events = load(file)
            assert len(events) == scene['events']
            for event in events:
                assert type(event['source_frame']) is int and 8912 <= event['source_frame'] <= 10873
                assert event['direction'] in ['A->B', 'B->A']
                assert float(event['time_s']) == event['source_frame']/25
            counts = Counter(e['direction'] for e in events)
            assert counts['A->B'] == scene['A_to_B'] and counts['B->A'] == scene['B_to_A']
            records.append({'condition_id': stage + '/' + condition['name'], 'title': condition['title'],
                'checkpoint_sha256': condition['checkpoint_sha256'], 'seed': condition['seed'],
                'orientation': condition.get('orientation', 'original'),
                'source_sha256': SOURCE_SHA, 'source_frame_scope': [8912, 10873], 'history_start': 0,
                'summary_path': str(summary_path), 'summary_sha256': sha(summary_path),
                'protocol_path': str(folder / protocol), 'protocol_sha256': sha(folder / protocol),
                'events_path': str(file), 'events_sha256': sha(file),
                'predicted_A_to_B': counts['A->B'], 'predicted_B_to_A': counts['B->A'],
                'predicted_events': len(events), 'source_accuracy_verified': False})
    assert len(records) == 17
    assert len({(r['checkpoint_sha256'], r['orientation']) for r in records}) == 17
    # Earlier threeCowsoriginal traces are exact priorversions of currentoriginals.
    aliases = []
    old_folder = PROJECT / 'cows2021_adaptation_20261027/delivery/results/inference'
    old = load(old_folder / 'summary.json')
    for condition in old['conditions']:
        match = next(r for r in records if r['checkpoint_sha256'] == condition['checkpoint_sha256'] and r['orientation'] == 'original')
        path = old_folder / condition['name'] / 'source_events.json'
        assert normalized(load(path)) == normalized(load(match['events_path']))
        aliases.append({'historical_condition': 'cows2021_adaptation_20261027/' + condition['name'],
                        'canonical_condition': match['condition_id'], 'normalized_events_equal': True,
                        'historical_events_path': str(path), 'historical_events_sha256': sha(path)})
    legacy = PROJECT / 'source_demo_20261026/delivery/results/preview'
    legacy_counts = []
    for name in ['generic', 'pilot']:
        match = next(r for r in records if r['condition_id'] == 'detector_training_20261027/' + name)
        path = legacy / f'{name}_predicted_events.json'
        same = normalized(load(path)) == normalized(load(match['events_path']))
        # Keep this as history evidence; no assertion that every originalruntime
        # or trackID was identical simply because events match.
        legacy_counts.append({'historical_name': 'source_demo_20261026/' + name,
                              'latest_same_checkpoint': match['condition_id'],
                              'normalized_event_frames_and_directions_equal': same,
                              'historical_events_path': str(path), 'historical_events_sha256': sha(path)})
    catalog = {'status': '17_FROZEN_SAME_SCOPE_PREDICTION_CONDITIONS_INDEXED',
               'source_sha256': SOURCE_SHA, 'frame_scope_inclusive': [8912, 10873],
               'FPS': 25, 'conditions': records, 'exact_prior_event_aliases': aliases,
               'legacy_preview_comparisons': legacy_counts,
               'selection_rule': 'All5completed detectorreplays +all6compositionconditions +all6orientationconditions; Cowsoriginal aliases included once.',
               'other_scope_tracker_Toros_conditions_not_claimed_as_source_replays': True,
               'new_inference': False, 'new_reference_received': False, 'source_count_accuracy_verified': False,
               'whole_goal_complete': False}
    target.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding='utf-8')
    columns = ['condition_id', 'title', 'seed', 'orientation', 'predicted_A_to_B', 'predicted_B_to_A', 'checkpoint_sha256']
    with (ROOT / 'results/frozen_prediction_catalog.csv').open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows({k: r[k] for k in columns} for r in records)
    print(json.dumps({'status': catalog['status'], 'conditions': len(records), 'Cows_aliases': len(aliases),
                      'legacy_frame_event_matches': legacy_counts,
                      'source_count_accuracy_verified': False}))


if __name__ == '__main__': main()
