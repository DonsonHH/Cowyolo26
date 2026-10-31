"""Analyze frozen development retrieval outputs without new inference."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import csv, hashlib, json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT.parent / 'integer_qat_20261028/delivery/results/study'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def save(path, value): Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    out = ROOT / 'results'
    out.mkdir(parents=True, exist_ok=True)
    assert not (out / 'summary.json').exists()
    source = load(STUDY / 'summary.json')
    assert source['status'] == 'TWELVE_CONDITIONS_PAIRED_INTEGER_QAT_DEVELOPMENT_COMPLETE'
    index = load(STUDY / 'validation_index.json')
    g_index, q_index = index['gallery'], index['queries']
    ids = sorted({r['identity'] for r in g_index})
    assert len(ids) == 5 and len(q_index) == 55
    files = [STUDY / 'summary.json', STUDY / 'validation_index.json', STUDY / 'all_models_thresholds_frozen.json']
    for r in source['conditions']:
        p = STUDY / f'seed{r["seed"]}_{r["condition"]}'
        files.extend([p / 'validation_embeddings.npz', p / 'predictions.json', p / 'threshold.json', p / 'result.json'])
    protocol = {'name': 'Frozen QAT development retrieval risk decomposition v1',
                'created_UTC': datetime.now(timezone.utc).isoformat(),
                'input_files': [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in files],
                'seeds': [26, 27, 28], 'conditions': ['source_folded_fp32', 'initial_integer', 'paired_float_continuation', 'integer_forward_qat'],
                'analysis': ['FrozenC/W/U and correct-ranking-reject/wrong-ranking-reject',
                             'Peranonymousidentity counts and top1/top2 margins',
                             'Trueidentity vs strongestotheridentity scores; unknownbestscore',
                             'Pairedfloat-vsQAT outcome transitions for samequery',
                             'Enumerateallwrongacceptedqueries and allunknownfalseaccepts for qualitative followup'],
                'selection': 'All12frozenconditions, all55existingqueries; no newthresholds/modelselection/inference/training.',
                'figure': 'Primary6pairedfloat/QATconditions, same scoreaxes, knowncorrect/rejected/wrong andunknown scores shown withfrozenthreshold.',
                'new_independent_test_or_board_claim': False, 'whole_goal_complete': False}
    protocol_path = ROOT / 'protocol/frozen_risk_v1.json'
    protocol_path.parent.mkdir(parents=True, exist_ok=True)
    assert not protocol_path.exists()
    save(protocol_path, protocol)
    all_rows, conditions, per_id, errors = [], [], [], []
    for condition in source['conditions']:
        seed, name = condition['seed'], condition['condition']
        path = STUDY / f'seed{seed}_{name}'
        embeddings = np.load(path / 'validation_embeddings.npz')
        gallery, queries = embeddings['gallery'].astype(float), embeddings['queries'].astype(float)
        similarities = queries @ gallery.T
        scores = np.stack([similarities[:, [j for j, r in enumerate(g_index) if r['identity'] == identity]].max(1) for identity in ids], axis=1)
        frozen = load(path / 'predictions.json')
        threshold = condition['threshold']['threshold']
        rows = []
        for i, (metadata, previous, values) in enumerate(zip(q_index, frozen, scores)):
            ranks = sorted(range(len(ids)), key=lambda k: (-float(values[k]), k))
            first, second = ranks[:2]
            predicted = ids[first]
            known = metadata['identity'] in ids
            best = float(values[first])
            accepted = best >= threshold
            correct = known and predicted == metadata['identity']
            if known:
                outcome = 'C' if accepted and correct else 'W' if accepted else 'U_rank_correct' if correct else 'U_rank_wrong'
                true_index = ids.index(metadata['identity'])
                genuine = float(values[true_index])
                impostor = float(max(v for j, v in enumerate(values) if j != true_index))
                rank = ranks.index(true_index) + 1
            else:
                outcome = 'unknown_false_accept' if accepted else 'unknown_reject'
                genuine = impostor = rank = None
            assert previous['predicted_id'] == predicted and previous['accepted'] == accepted
            assert previous['similarity'] == best and previous['is_known'] == known
            row = {'seed': seed, 'condition': name, 'query_index': i,
                   'relative_path': metadata['relative_path'], 'identity': metadata['identity'],
                   'known': known, 'predicted_id': predicted, 'top1_score': best, 'top2_score': float(values[second]),
                   'top1_top2_margin': best - float(values[second]), 'threshold': threshold,
                   'threshold_gap': best - threshold, 'accepted': accepted, 'rank_correct': correct,
                   'true_rank': rank, 'true_identity_score': genuine, 'strongest_other_identity_score': impostor,
                   'genuine_other_margin': genuine - impostor if known else None, 'outcome': outcome}
            rows.append(row)
            if outcome in ['W', 'unknown_false_accept']:
                top_gallery = max((j for j, r in enumerate(g_index) if r['identity'] == predicted), key=lambda j: (similarities[i, j], -j))
                error = {**row, 'query_source': metadata, 'predicted_gallery_source': g_index[top_gallery]}
                if known:
                    true_gallery = max((j for j, r in enumerate(g_index) if r['identity'] == metadata['identity']), key=lambda j: (similarities[i, j], -j))
                    error['true_gallery_source'] = g_index[true_gallery]
                errors.append(error)
        counts = Counter(r['outcome'] for r in rows)
        known_rows = [r for r in rows if r['known']]
        unknown_rows = [r for r in rows if not r['known']]
        closed = sum(r['rank_correct'] for r in rows)
        metrics = condition['validation']
        assert counts['C'] == metrics['known_correct_accepted_C'] and counts['W'] == metrics['known_wrong_accepted_W']
        assert counts['U_rank_correct'] + counts['U_rank_wrong'] == metrics['known_rejected_U']
        assert closed == metrics['known_closed_top1_correct'] and counts['unknown_false_accept'] == metrics['unknown_false_accepts']
        record = {'seed': seed, 'condition': name, 'threshold': threshold, 'known_queries': len(known_rows),
                  'unknown_queries': len(unknown_rows), 'C': counts['C'], 'W': counts['W'],
                  'U_rank_correct': counts['U_rank_correct'], 'U_rank_wrong': counts['U_rank_wrong'],
                  'closed_top1_correct': closed, 'unknown_false_accepts': counts['unknown_false_accept'],
                  'known_true_score_median': float(np.median([r['true_identity_score'] for r in known_rows])),
                  'known_true_minus_other_median': float(np.median([r['genuine_other_margin'] for r in known_rows])),
                  'unknown_best_score_median': float(np.median([r['top1_score'] for r in unknown_rows])),
                  'unknown_best_score_second_highest': float(sorted(r['top1_score'] for r in unknown_rows)[-2]),
                  'known_threshold_exact_ties': sum(r['threshold_gap'] == 0 for r in known_rows)}
        conditions.append(record)
        for identity in sorted({r['identity'] for r in rows}):
            group = [r for r in rows if r['identity'] == identity]
            per_id.append({'seed': seed, 'condition': name, 'identity': identity, 'known': group[0]['known'],
                           'queries': len(group), 'outcomes': dict(Counter(r['outcome'] for r in group)),
                           'mean_top1_score': float(np.mean([r['top1_score'] for r in group])),
                           'mean_top1_top2_margin': float(np.mean([r['top1_top2_margin'] for r in group]))})
        all_rows.extend(rows)
    paired = []
    for seed in [26, 27, 28]:
        a = [r for r in all_rows if r['seed'] == seed and r['condition'] == 'paired_float_continuation']
        b = [r for r in all_rows if r['seed'] == seed and r['condition'] == 'integer_forward_qat']
        assert len(a) == len(b) == 55
        transitions = Counter()
        for left, right in zip(a, b):
            assert left['relative_path'] == right['relative_path']
            transitions[(left['outcome'], right['outcome'])] += 1
        paired.append({'seed': seed, 'transitions': [{'float': left, 'QAT': right, 'queries': count}
                       for (left, right), count in sorted(transitions.items())]})
    assert len(all_rows) == 660 and len(conditions) == 12 and len(per_id) == 132
    save(out / 'per_query660.json', all_rows)
    save(out / 'per_identity132.json', per_id)
    save(out / 'all_wrong_and_unknown_accepts.json', errors)
    save(out / 'paired_outcome_transitions.json', paired)
    with (out / 'condition12_decomposition.csv').open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(conditions[0]))
        writer.writeheader()
        writer.writerows(conditions)
    result = {'status': 'ALL12_FROZEN_RISK_CONDITIONS_AND660_QUERIES_DECOMPOSED',
              'protocol_sha256': sha(protocol_path), 'conditions': conditions, 'paired_transitions': paired,
              'known_queries_per_condition': 25, 'unknown_queries_per_condition': 30,
              'condition_rows': 12, 'query_condition_rows': 660, 'identity_condition_rows': 132,
              'all_error_rows_including_unknown_accepts': len(errors),
              'new_forward_training_threshold_selection_or_final_test': False,
              'FPGA_execution_verified': False, 'whole_goal_complete': False}
    save(out / 'summary.json', result)
    print(json.dumps({'status': result['status'], 'QAT': [r for r in conditions if r['condition'] == 'integer_forward_qat'],
                      'paired_float': [r for r in conditions if r['condition'] == 'paired_float_continuation'],
                      'error_rows': len(errors), 'whole_goal_complete': False}))


if __name__ == '__main__': main()
