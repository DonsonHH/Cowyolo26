"""Score reviewed directional video totals without inventing timed event ground truth."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from .protocol import canonical_gate, gate_from_config

DIRECTIONS = ('A->B', 'B->A')
VERSION = 'reviewed-directional-video-totals-v1'


def _integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(name + ' must be a nonnegative integer')
    return value


def score_totals(summary, predictions, reference):
    """A reviewed total supports count errors, never event precision or recall."""
    if summary.get('status') != 'COMPLETED_UNSCORED':
        raise ValueError('A completed run is required')
    if reference.get('reference_type') != 'REVIEWED_VIDEO_DIRECTIONAL_TOTALS':
        raise ValueError('Use a reviewed directional-total reference')
    review = reference.get('review', {})
    if (reference.get('review_status') != 'reviewed' or not review.get('reviewer')
            or not review.get('statement') or not review.get('evidence')
            or review.get('view') not in {'source_only', 'prediction_overlay', 'unspecified'}):
        raise ValueError('The actual human statement, evidence and viewing mode are required')
    for key in ('video_id',):
        if not summary.get(key) or reference.get(key) != summary[key]:
            raise ValueError('Video identity differs')
    digest = reference.get('source_video_sha256')
    if (not isinstance(digest, str) or len(digest) != 64
            or any(c not in '0123456789abcdef' for c in digest)
            or digest != summary.get('video_sha256')):
        raise ValueError('Reference and runtime source hashes differ')
    interval = reference['reviewed_interval']
    start = _integer(interval['start_frame0'], 'start_frame0')
    end = _integer(interval['end_frame0'], 'end_frame0')
    config = summary['config']
    if (end < start or config.get('scope_start_frame0', 0) != start
            or config.get('end_frame0_exclusive') != end + 1):
        raise ValueError('Reference and run counting intervals differ')
    if canonical_gate(reference['review_gate']) != gate_from_config(config):
        raise ValueError('Reference and runtime counting geometry differ')
    origin = config['in_direction']
    if origin not in DIRECTIONS:
        raise ValueError('Unknown configured direction')
    if not summary.get('run_id') or not summary.get('session_id'):
        raise ValueError('Runtime run and session identifiers are required')
    totals = reference.get('directional_totals', {})
    if set(totals) != set(DIRECTIONS):
        raise ValueError('Declare both directions, using null for an unreviewed direction')
    reviewed = {direction: _integer(value, direction) for direction, value in totals.items() if value is not None}
    if not reviewed:
        raise ValueError('At least one direction must have an actual reviewed total')
    counts, ids = Counter(), set()
    for row in predictions:
        if any(row.get(k) != summary[k] for k in ('video_id', 'session_id', 'run_id')):
            raise ValueError('Prediction scope differs from the run')
        event_id = row.get('event_id')
        if not isinstance(event_id, str) or not event_id.strip() or event_id in ids:
            raise ValueError('Prediction event identifiers must be unique and nonempty')
        ids.add(event_id)
        frame = _integer(row['frame0'], 'prediction frame0')
        if not start <= frame <= end or row.get('direction') not in DIRECTIONS:
            raise ValueError('Prediction lies outside the declared interval or direction')
        expected_kind = 'IN' if row['direction'] == origin else 'OUT'
        if row.get('kind') != expected_kind:
            raise ValueError('Prediction direction and IN/OUT kind disagree')
        counts[expected_kind] += 1
    if summary['counts'] != {'IN': counts['IN'], 'OUT': counts['OUT'], 'NET': counts['IN']-counts['OUT']}:
        raise ValueError('Event ledger and terminal count summary disagree')
    opposite = DIRECTIONS[1] if origin == DIRECTIONS[0] else DIRECTIONS[0]
    actual = {origin: counts['IN'], opposite: counts['OUT']}
    errors = {d: actual[d] - total for d, total in reviewed.items()}
    absolute = {d: abs(value) for d, value in errors.items()}
    return {
        'metric_version': VERSION, 'status': 'SCORED_AGAINST_REVIEWED_VIDEO_TOTALS',
        'video_id': summary['video_id'], 'run_id': summary['run_id'], 'session_id': summary['session_id'],
        'source_video_sha256': digest, 'reviewed_interval': interval,
        'reviewed_directions': sorted(reviewed), 'reference_totals': reviewed,
        'predicted_directional_totals': actual, 'signed_errors': errors,
        'absolute_errors': absolute, 'absolute_error_over_reviewed_directions': sum(absolute.values()),
        'all_reviewed_totals_agree': all(value == 0 for value in absolute.values()),
        'unreviewed_directions': sorted(set(DIRECTIONS)-set(reviewed)),
        'review': review, 'data_role': reference.get('data_role', 'unspecified'),
        'source_session_independence_verified': False,
        'event_precision': None, 'event_recall': None, 'event_f1': None,
        'count_agreement_proves_no_misses_or_duplicates': False,
    }


def aggregate_totals(scores):
    """Aggregate one run per video unit; repeats must be reported separately."""
    if not scores:
        raise ValueError('At least one scored video is required')
    keys = set()
    for row in scores:
        if row.get('status') != 'SCORED_AGAINST_REVIEWED_VIDEO_TOTALS' or row.get('metric_version') != VERSION:
            raise ValueError('Aggregate only verified directional-total scores')
        key = (row['source_video_sha256'], row['reviewed_interval']['start_frame0'],
               row['reviewed_interval']['end_frame0'])
        if key in keys:
            raise ValueError('Repeated source intervals do not create independent video units')
        keys.add(key)
    n = len(scores)
    total = sum(row['absolute_error_over_reviewed_directions'] for row in scores)
    agrees = sum(row['all_reviewed_totals_agree'] for row in scores)
    return {'metric_version': VERSION, 'video_units': n,
            'sum_absolute_error_over_reviewed_directions': total,
            'mean_absolute_error_over_reviewed_directions_per_video': total/n,
            'exact_agreement_video_units': agrees, 'exact_agreement_fraction': agrees/n,
            'viewing_modes': sorted({row['review']['view'] for row in scores}),
            'source_session_independence_verified': False,
            'event_precision': None, 'event_recall': None, 'event_f1': None}


def score_files(run_folder, reference_path):
    run_folder, reference_path = Path(run_folder), Path(reference_path)
    summary_path, events_path = run_folder/'summary.json', run_folder/'events.jsonl'
    summary = json.loads(summary_path.read_bytes())
    prediction = [json.loads(line) for line in events_path.read_bytes().splitlines()]
    result = score_totals(summary, prediction, json.loads(reference_path.read_text(encoding='utf-8-sig')))
    result['input_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (summary_path, events_path, reference_path)}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = score_files(args.run, args.reference)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
