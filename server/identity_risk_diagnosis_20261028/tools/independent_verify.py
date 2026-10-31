from pathlib import Path
from collections import Counter
import hashlib, json, math
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    protocol_path = ROOT / 'protocol/frozen_risk_v1.json'
    p = load(protocol_path)
    for row in p['input_files']:
        path = Path(row['path'])
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
    study = Path(p['input_files'][0]['path']).parent
    model_summary = load(study / 'summary.json')
    index = load(study / 'validation_index.json')
    ids = sorted({r['identity'] for r in index['gallery']})
    analysis = load(ROOT / 'results/summary.json')
    rows = load(ROOT / 'results/per_query660.json')
    groups = load(ROOT / 'results/per_identity132.json')
    errors = load(ROOT / 'results/all_wrong_and_unknown_accepts.json')
    assert analysis['protocol_sha256'] == sha(protocol_path)
    checks, maximum, dot_products, boundary_cases = [], 0., 0, 0
    expected_errors = []
    for source in model_summary['conditions']:
        seed, name = source['seed'], source['condition']
        directory = study / f'seed{seed}_{name}'
        embeddings = np.load(directory / 'validation_embeddings.npz')
        g, q = embeddings['gallery'], embeddings['queries']
        saved = load(directory / 'predictions.json')
        actual = [r for r in rows if r['seed'] == seed and r['condition'] == name]
        assert len(actual) == len(saved) == 55
        counts = Counter()
        for i, (metadata, primary, result) in enumerate(zip(index['queries'], saved, actual)):
            # Different summation path for everyquery/galleryscore.
            scores = [math.fsum(float(a) * float(b) for a, b in zip(q[i], sample)) for sample in g]
            dot_products += len(scores)
            by_id = {identity: max(score for score, item in zip(scores, index['gallery']) if item['identity'] == identity) for identity in ids}
            ranked = sorted(ids, key=lambda identity: (-by_id[identity], identity))
            assert ranked[0] == primary['predicted_id'] == result['predicted_id']
            maximum = max(maximum, abs(by_id[ranked[0]] - result['top1_score']), abs(by_id[ranked[1]] - result['top2_score']))
            assert abs((by_id[ranked[0]] - by_id[ranked[1]]) - result['top1_top2_margin']) <= 1e-12
            known = metadata['identity'] in ids
            rank_correct = known and metadata['identity'] == primary['predicted_id']
            accepted = primary['accepted']
            threshold = source['threshold']['threshold']
            if abs(primary['similarity'] - threshold) > 1e-12:
                assert (by_id[ranked[0]] >= threshold) == accepted
            else:
                boundary_cases += 1
                # Frozendefinition usesexact savedscore/threshold; audit tolerance
                # is for alternative summation only, not a changeddecision rule.
                assert accepted == (primary['similarity'] >= threshold)
            if known:
                outcome = ('C' if rank_correct else 'W') if accepted else ('U_rank_correct' if rank_correct else 'U_rank_wrong')
                genuine = by_id[metadata['identity']]
                other = max(score for identity, score in by_id.items() if identity != metadata['identity'])
                assert result['true_rank'] == ranked.index(metadata['identity']) + 1
                assert abs(genuine - result['true_identity_score']) <= 1e-12
                assert abs(other - result['strongest_other_identity_score']) <= 1e-12
            else:
                outcome = 'unknown_false_accept' if accepted else 'unknown_reject'
            assert outcome == result['outcome'] and known == result['known']
            assert result['relative_path'] == primary['relative_path'] == metadata['relative_path']
            counts[outcome] += 1
            if outcome in ['W', 'unknown_false_accept']:
                expected_errors.append((seed, name, metadata['relative_path'], outcome))
        record = next(r for r in analysis['conditions'] if r['seed'] == seed and r['condition'] == name)
        assert all(counts[key] == record[key] for key in ['C', 'W', 'U_rank_correct', 'U_rank_wrong'])
        assert counts['unknown_false_accept'] == record['unknown_false_accepts']
        for identity in sorted({r['identity'] for r in actual}):
            group = next(r for r in groups if r['seed'] == seed and r['condition'] == name and r['identity'] == identity)
            expected = Counter(r['outcome'] for r in actual if r['identity'] == identity)
            assert group['queries'] == sum(expected.values()) == 5 and group['outcomes'] == dict(expected)
        checks.append({'seed': seed, 'condition': name, 'counts': dict(counts)})
    assert maximum <= 1e-12 and dot_products == 16500
    assert sorted(expected_errors) == sorted((r['seed'], r['condition'], r['relative_path'], r['outcome']) for r in errors)
    paired = load(ROOT / 'results/paired_outcome_transitions.json')
    for case in paired:
        left = {r['relative_path']: r['outcome'] for r in rows if r['seed'] == case['seed'] and r['condition'] == 'paired_float_continuation'}
        right = {r['relative_path']: r['outcome'] for r in rows if r['seed'] == case['seed'] and r['condition'] == 'integer_forward_qat'}
        actual = Counter((left[path], right[path]) for path in left)
        assert actual == Counter({(r['float'], r['QAT']): r['queries'] for r in case['transitions']})
    coverage = load(ROOT / 'results/matched_coverage.json')
    cp = load(ROOT / 'protocol/matched_coverage_v1.json')
    assert cp['perquery_sha256'] == sha(ROOT / 'results/per_query660.json')
    for condition in coverage['results']:
        items = [r for r in rows if r['seed'] == condition['seed'] and r['condition'] == 'integer_forward_qat']
        correct_scores = sorted([r['top1_score'] for r in items if r['known'] and r['rank_correct']], reverse=True)
        threshold = correct_scores[condition['target_float_C'] - 1]
        assert threshold == condition['hypothetical_QAT_threshold']
        accepted = [r for r in items if r['top1_score'] >= threshold]
        assert sum(not r['known'] for r in accepted) == condition['unknown_false_accepts']
        assert sum(r['known'] and not r['rank_correct'] for r in accepted) == condition['W']
    result = {'status': 'ALL660_QUERY_OUTCOMES_132_IDENTITY_GROUPS_AND_MATCHED_COVERAGE_INDEPENDENTLY_VERIFIED',
              'protocol_sha256': sha(protocol_path), 'source_summary_sha256': sha(ROOT / 'results/summary.json'),
              'query_condition_rows': 660, 'identity_condition_rows': 132, 'independent_fsum_dotproducts': dot_products,
              'maximum_alternative_summation_score_difference': maximum,
              'near_threshold_cases_using_frozen_exact_decision': boundary_cases,
              'counterfactual_operating_points': 3, 'all_error_rows': len(errors),
              'new_inference_training_or_adopted_thresholds': False,
              'whole_goal_complete': False}
    target = ROOT / 'results/independent_verification.json'
    assert not target.exists()
    target.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__': main()
