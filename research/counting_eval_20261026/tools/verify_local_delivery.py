"""Verify transferred evidence and independently recompute the six-event result.

Does not import the counter, scorer, numpy or scipy used in the server run.
The exhaustive matcher is practical only for this small reference sample.
"""
from pathlib import Path
from collections import defaultdict
from functools import lru_cache
import csv
import hashlib
import json
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    record = json.loads((ROOT/'results/bundle_record.json').read_text())
    bundle = ROOT/'results/counting_evaluation_delivery.tar.gz'
    assert bundle.stat().st_size == record['bytes']
    assert sha(bundle) == record['sha256']
    dest = ROOT/'delivery'
    if not dest.exists():
        dest.mkdir()
        with tarfile.open(bundle) as tf:
            tf.extractall(dest, filter='data')
    delivered = dest/'counting_evaluation'
    manifest = json.loads((delivered/'evidence/delivery_manifest.json').read_text())
    for row in manifest:
        p = (delivered/row['path']).resolve()
        assert p.is_relative_to(delivered.resolve())
        assert p.stat().st_size == row['bytes'] and row['bytes'] > 0, row
        assert sha(p) == row['sha256'], row
    assert len(manifest)+1 == record['file_count']
    # Frozen annotations and code in the bundle must match their local originals.
    copied = []
    for category, local in [('annotations', 'annotations'), ('code', 'tools')]:
        for p in (delivered/category).iterdir():
            q = ROOT/local/p.name
            if q.exists():
                assert sha(q) == sha(p), p.name
                copied.append(p.name)
    rows = list(csv.reader((delivered/'annotations/publisher_gt_original.txt').open()))
    gt = [list(map(float, r)) for r in rows]
    ids = defaultdict(list)
    seen = set()
    for r in gt:
        f, tid = int(r[0]), int(r[1])
        assert (f, tid) not in seen
        seen.add((f, tid))
        assert 0 <= f < 479 and r[4] > 0 and r[5] > 0
        cx, cy = (r[2]+r[4]/2)/1920, (r[3]+r[5]/2)/1080
        if .1 < cy < .95 and 0 <= cx <= 1:
            ids[tid].append((f, 'A' if cx < .4 else 'B' if cx > .6 else 'M'))
    # Derive stable-region visits by grouping consecutive region-labelled frames.
    reference = []
    for tid, observations in ids.items():
        observations.sort()
        groups = []
        for f, region in observations:
            if groups and groups[-1][-1][0]+1 == f and groups[-1][-1][1] == region:
                groups[-1].append((f, region))
            else:
                groups.append([(f, region)])
        origin = None
        previous_last = None
        for run in groups:
            if previous_last is not None and run[0][0]-previous_last > 60:
                origin = None
            previous_last = run[-1][0]
            if run[0][1] == 'M' or len(run) < 3:
                continue
            region = run[0][1]
            if origin is not None and origin != region:
                frame = run[2][0]
                reference.append({'track_id': tid, 'frame': frame,
                                  'time_s': frame/30, 'direction': origin+'->'+region})
            origin = region
    reference.sort(key=lambda r: (r['time_s'], r['track_id']))
    publisher = json.loads((delivered/'evidence/author_gt_summary.json').read_text())
    assert reference == publisher['events']
    assert len(gt) == 1775 and len({int(r[1]) for r in gt}) == 9
    all_runs = json.loads((delivered/'evidence/external_inference_summaries.json').read_text())
    protocol = json.loads((ROOT/'annotations/evaluation_protocol_v1.json').read_text())
    scored = json.loads((delivered/'evidence/metrics.json').read_text())
    assert len(all_runs) == 14
    recomputed = []
    for run in all_runs:
        assert run['source_frames'] == run['processed_frames'] > 0
        assert run['model_sha256'] == protocol['weights'][run['model']]['sha256']
        assert (run['input_size'], run['confidence'], run['gate_fraction'],
                run['stable_samples'], run['maximum_gap_s']) == (320, .2, [.4, .6], 3, 2)
        if run['video'] != 'Toros':
            continue
        predictions = run['events']
        @lru_cache(None)
        def exhaustive(i, used):
            if i == len(reference):
                return (0, 0., ())
            best = exhaustive(i+1, used)
            for j, pred in enumerate(predictions):
                err = abs(reference[i]['time_s']-pred['time_s'])
                if used & (1 << j) or err > 2:
                    continue
                n, cost, pairs = exhaustive(i+1, used | (1 << j))
                candidate = (n+1, cost+err, ((i, j),)+pairs)
                if (candidate[0], -candidate[1]) > (best[0], -best[1]):
                    best = candidate
            return best
        n, error, pairs = exhaustive(0, 0)
        tp = sum(reference[i]['direction'] == predictions[j]['direction'] for i, j in pairs)
        fp, fn = len(predictions)-tp, len(reference)-tp
        f1 = 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None
        expected = next(r for r in scored['frozen_external_results'] if r['model'] == run['model'])['event_metrics']
        assert (tp, fp, fn, f1) == tuple(expected[k] for k in ('TP', 'FP', 'FN', 'f1'))
        recomputed.append({'model': run['model'], 'TP': tp, 'FP': fp, 'FN': fn,
                           'f1': f1, 'temporally_matched': n, 'summed_time_error_s': error,
                           'pairs': pairs})
    weight = ROOT.parent/'data_audit_20261026/models/yolo26n_opencows_5epoch_dev.pt'
    assert sha(weight) == protocol['weights']['pilot']['sha256']
    result = {'status': 'PASS', 'bundle_sha256': record['sha256'],
              'verified_manifest_files': len(manifest), 'matched_local_inputs': copied,
              'independent_reference_events': reference,
              'independent_exhaustive_event_matching': recomputed,
              'full_frame_coverage_runs': len(all_runs), 'pilot_checkpoint_verified': True,
              'scope': 'Evidence integrity and independent sample arithmetic; not field validation'}
    (ROOT/'results/local_independent_verification.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ['matched_local_inputs', 'independent_reference_events']}, indent=2))


if __name__ == '__main__':
    main()
