from pathlib import Path
from collections import Counter, defaultdict
import hashlib, json, os
import numpy as np
import torch

PROJECT = Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT = PROJECT / 'activation_range_20261028'
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text())


def int_convolution(centered, weights, stride, padding, dilation, groups):
    x, w = centered.astype(np.int64), weights.astype(np.int64)
    n, channels, height, width = x.shape
    outputs, per_group, kh, kw = w.shape
    py, px = padding
    sy, sx = stride
    dy, dx = dilation
    assert channels == per_group * groups and outputs % groups == 0
    padded = np.pad(x, ((0, 0), (0, 0), (py, py), (px, px)))
    window = np.lib.stride_tricks.sliding_window_view(padded, ((kh-1)*dy+1, (kw-1)*dx+1), axis=(2, 3))
    window = window[:, :, ::sy, ::sx, ::dy, ::dx]
    oh, ow = window.shape[2:4]
    value = np.empty((n, outputs, oh, ow), dtype=np.int64)
    count = outputs // groups
    for group in range(groups):
        inputs = window[:, group*per_group:(group+1)*per_group]
        kernel = w[group*count:(group+1)*count]
        value[:, group*count:(group+1)*count] = np.einsum('ncyxij,mcij->nmyx', inputs, kernel, dtype=np.int64, optimize=True)
    return value


def main():
    assert os.environ.get('SLURM_JOB_ID') and __import__('socket').gethostname() != 'mu01'
    torch.set_num_threads(2)
    pp = ROOT / 'protocol/activation_range_v1.json'
    p = load(pp)
    folder = ROOT / 'results/probe'
    summary = load(folder / 'summary.json')
    assert summary['protocol_sha256'] == sha(pp)
    assert summary['actual_optimizer_updates'] == summary['validation_or_test_image_reads'] == 0
    assert summary['model_weights_and_qparams_unchanged'] is True
    for row in p['models']: assert sha(row['remote_path']) == row['sha256']
    manifest = PROJECT / 'identity_training/results/input_audit/manifest.json'
    assert sha(manifest) == p['manifest_sha256']
    lookup = {r['relative_path']: r for r in load(manifest)}
    access = load(folder / 'training_image_access.json')
    assert len(access) == len({r['relative_path'] for r in access}) == 64
    for row in access:
        assert row['split'] == lookup[row['relative_path']]['split'] == 'train'
        assert row['sha256'] == lookup[row['relative_path']]['sha256'] == sha(PROJECT / 'identity_training' / row['relative_path'])
    stats = load(folder / 'layer_statistics.json')
    assert len(stats) == 1872
    aggregate = defaultdict(lambda: [0, 0, 0, 0])
    denominators = {}
    for row in stats:
        key = row['seed'], row['condition'], row['view']
        for prefix in ['input', 'output']:
            total = row[prefix + '_elements']
            values = [row[prefix + '_' + k] for k in ['below', 'above', 'at_min', 'at_max']]
            assert all(isinstance(v, int) and v >= 0 for v in values) and sum(values) <= total
            assert row[prefix + '_outside_fraction'] == sum(values[:2]) / total
        aggregate[key][0] += row['input_elements']
        aggregate[key][1] += row['input_below'] + row['input_above']
        aggregate[key][2] += row['output_elements']
        aggregate[key][3] += row['output_below'] + row['output_above']
        old = denominators.setdefault(row['module'], (row['input_elements'], row['output_elements']))
        assert old == (row['input_elements'], row['output_elements'])
    assert len(denominators) == 52 and len(aggregate) == 36
    features = np.load(folder / 'feature_vectors.npz')
    metric_checks = []
    for row in summary['conditions']:
        key = row['seed'], row['condition'], row['view']
        counts = aggregate[key]
        assert row['weighted_input_outside_fraction'] == counts[1] / counts[0]
        assert row['weighted_output_outside_fraction'] == counts[3] / counts[2]
        name = f'seed{row["seed"]}_{row["condition"]}_{row["view"]}'
        a = features[name].astype(np.float64)
        b = features[f'seed{row["seed"]}_teacher_{row["view"]}'].astype(np.float64)
        assert a.shape == b.shape == (64, 576) and np.isfinite(a).all() and np.isfinite(b).all()
        cos = np.einsum('ij,ij->i', a, b) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1))
        assert abs(float(cos.mean()) - row['mean_teacher_cosine']) < 1e-12
        assert abs(float(np.median(cos)) - row['median_teacher_cosine']) < 1e-12
        assert np.max(np.abs(cos - features[name + '_teacher_cosine'])) < 1e-12
        assert float(np.mean((a-b)**2)) == row['mean_teacher_feature_MSE']
        metric_checks.append({'seed': row['seed'], 'condition': row['condition'], 'view': row['view'],
                              'mean_teacher_cosine': float(cos.mean()),
                              'input_outside_fraction': counts[1]/counts[0], 'output_outside_fraction': counts[3]/counts[2]})
    fixtures = np.load(folder / 'arithmetic_fixtures.npz')
    index = load(folder / 'arithmetic_fixture_index.json')
    assert len(index) == 72
    states = {}
    comparisons, accumulator_elements = [], 0
    for fixture in index:
        model_path = fixture['source_state']['remote_path']
        if model_path not in states:
            assert sha(model_path) == fixture['source_state']['sha256']
            states[model_path] = torch.load(model_path, map_location='cpu', weights_only=True)
        state = states[model_path]
        prefix, key = fixture['module'] + '.', fixture['key']
        sx = state[prefix + 'sx'].numpy().reshape(())
        zx = state[prefix + 'zx'].numpy().reshape(())
        sw = state[prefix + 'sw'].numpy()
        sy = state[prefix + 'sy'].numpy().reshape(())
        zy = state[prefix + 'zy'].numpy().reshape(())
        bias = state[prefix + 'conv.bias'].numpy()
        ix, iw = fixtures[key + '_ix'], fixtures[key + '_iw']
        qx = np.clip(ix, 0, 255) if fixture['act_clip'] else ix
        qw = np.clip(iw, -128, 127) if fixture['weight_clip'] else iw
        assert np.array_equal(qx, fixtures[key + '_qx']) and np.array_equal(qw, fixtures[key + '_qw'])
        assert np.array_equal(qx, np.rint(qx)) and np.array_equal(qw, np.rint(qw))
        centered = qx.astype(np.int64) - int(zx)
        bound = qw.shape[1] * qw.shape[2] * qw.shape[3] * int(np.max(np.abs(centered))) * int(np.max(np.abs(qw)))
        assert bound <= np.iinfo(np.int32).max
        acc = int_convolution(centered, qw, fixture['stride'], fixture['padding'], fixture['dilation'], fixture['groups'])
        actual = fixtures[key + '_acc']
        assert np.array_equal(acc.astype(np.float64), actual)
        raw = acc.astype(np.float64) * sx.astype(np.float64)
        raw = raw * sw.astype(np.float64).reshape(1, -1, 1, 1)
        raw = (raw + bias.astype(np.float64).reshape(1, -1, 1, 1)).astype(np.float32)
        assert np.array_equal(raw, fixtures[key + '_raw'])
        iy = np.rint(raw / sy).astype(np.float32) + zy.astype(np.float32)
        assert np.array_equal(iy, fixtures[key + '_iy'])
        y = (np.clip(iy, 0, 255) if fixture['act_clip'] else iy) - zy.astype(np.float32)
        y = y * sy.astype(np.float32)
        assert np.array_equal(y, fixtures[key + '_output'])
        stat = next(r for r in stats if r['seed'] == fixture['seed'] and r['condition'] == fixture['condition'] and
                    r['view'] == fixture['view'] and r['module'] == fixture['module'])
        assert stat['input_elements'] == ix.size * 64 and stat['output_elements'] == iy.size * 64
        accumulator_elements += acc.size
        comparisons.append({'seed': fixture['seed'], 'condition': fixture['condition'], 'view': fixture['view'],
                            'layer': fixture['layer_index'], 'integer_accumulator_elements': acc.size,
                            'exact_INT64_accumulator_raw_and_output': True})
    weights = load(folder / 'weight_statistics.json')
    assert len(weights) == 936
    assert all(r['below'] + r['above'] + r['at_min'] + r['at_max'] <= r['elements'] for r in weights)
    assert len(summary['frozen_baseline_regression_gates']) == 6 and all(r['pass'] for r in summary['frozen_baseline_regression_gates'])
    counterfactuals = []
    for seed in [26, 27, 28]:
        for view in ['deterministic', 'augmented']:
            base = next(r for r in summary['conditions'] if (r['seed'], r['condition'], r['view']) == (seed, 'integer_forward_qat', view))
            for condition in ['QAT_no_activation_clipping', 'QAT_no_weight_clipping']:
                other = next(r for r in summary['conditions'] if (r['seed'], r['condition'], r['view']) == (seed, condition, view))
                counterfactuals.append({'seed': seed, 'view': view, 'condition': condition,
                                       'mean_teacher_cosine_difference': other['mean_teacher_cosine'] - base['mean_teacher_cosine']})
    result = {'status': '36_TRAIN_ONLY_METRICS_1872_COUNT_ROWS_AND72_ARITHMETIC_FIXTURES_INDEPENDENTLY_VERIFIED',
              'job_id': os.environ['SLURM_JOB_ID'], 'protocol_sha256': sha(pp), 'source_summary_sha256': sha(folder / 'summary.json'),
              'source_training_image_hashes': 64, 'validation_or_test_reads': 0,
              'condition_view_metrics': 36, 'feature_condition_image_rows': 2304,
              'layer_count_rows_arithmetic_checked': 1872, 'weight_count_rows_arithmetic_checked': 936,
              'representative_integer_fixtures': 72, 'fixture_accumulator_elements_recomputed': accumulator_elements,
              'full_1872_layer_tensor_values_independently_replayed': False,
              'counterfactual_effects': counterfactuals, 'all_counterfactuals_are_non_deployable_code_ranges': True,
              'new_training_updates': 0, 'FPGA_execution_verified': False, 'whole_goal_complete': False}
    path = ROOT / 'results/independent_verification.json'
    assert not path.exists()
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__': main()
