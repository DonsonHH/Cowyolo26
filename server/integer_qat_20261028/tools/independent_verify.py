"""Independent data-role, paired-update, export and retrieval verification."""
from pathlib import Path
import hashlib, json, os, sys
import numpy as np
import torch
PROJECT = Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT = PROJECT / 'integer_qat_20261028'
sys.path.insert(0, str(PROJECT / 'integer_trainable_20261028/tools'))
from smoke import runtime


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text())


def main():
    assert os.environ.get('SLURM_JOB_ID') and __import__('socket').gethostname() != 'mu01'
    torch.set_num_threads(2)
    p = load(ROOT / 'protocol/paired_integer_qat_v1.json')
    out = ROOT / 'results/study'
    summary = load(out / 'summary.json')
    assert summary['status'] == 'TWELVE_CONDITIONS_PAIRED_INTEGER_QAT_DEVELOPMENT_COMPLETE'
    assert summary['protocol_sha256'] == sha(ROOT / 'protocol/paired_integer_qat_v1.json')
    assert summary['formal_QAT_updates'] == summary['paired_float_updates'] == 360
    assert summary['smoke_updates_carried_into_training'] == 0
    assert summary['freeze_sha256'] == sha(out / 'all_models_thresholds_frozen.json')
    frozen = load(out / 'all_models_thresholds_frozen.json')
    assert len(frozen['conditions']) == 12
    assert frozen['protocol_sha256'] == summary['protocol_sha256']
    for observed, fixed in zip(summary['conditions'], frozen['conditions']):
        assert all(observed[k] == fixed[k] for k in ['seed', 'condition', 'model_sha256'])
        assert observed['threshold']['threshold'] == fixed['threshold']
    manifest_path = PROJECT / 'identity_training/results/input_audit/manifest.json'
    assert sha(manifest_path) == p['source_manifest_sha256']
    manifest = load(manifest_path)
    lookup = {r['relative_path']: r for r in manifest}
    train = [r for r in manifest if r['split'] == 'train']
    idx = load(out / 'validation_index.json')
    gallery, queries = idx['gallery'], idx['queries']
    assert len(gallery) == 25 and len(queries) == 55
    assert not {r['identity'] for r in train} & {r['identity'] for r in gallery + queries}
    access = load(out / 'image_access_log.json')
    assert len(access) == len({r['relative_path'] for r in access})
    for r in access:
        assert r['split'] in ['train', 'validation_gallery', 'validation_query']
        assert r['split'] == lookup[r['relative_path']]['split']
        assert r['sha256'] == lookup[r['relative_path']]['sha256'] == sha(PROJECT / 'identity_training' / r['relative_path'])
    pairs = []
    for source in p['source_models']:
        seed = source['seed']
        assert sha(source['path']) == source['sha256'] and sha(source['integer_initial_state']) == source['integer_initial_state_sha256']
        schedule = load(out / f'seed{seed}_schedule.json')['indices_into_training_rows']
        assert len(schedule) == 120
        for indices in schedule:
            assert len(indices) == len(set(indices)) == 32
            rows = [train[i] for i in indices]
            ids = sorted({r['identity'] for r in rows})
            assert len(ids) == 8 and all(sum(r['identity'] == identity for r in rows) == 4 for identity in ids)
            assert all(len({r['day'] for r in rows if r['identity'] == identity}) >= 2 for identity in ids)
        logs = [load(out / f'seed{seed}_{condition}_batches.json') for condition in ['paired_float_continuation', 'integer_forward_qat']]
        assert len(logs[0]) == len(logs[1]) == 120
        assert [r['training_input_sha256'] for r in logs[0]] == [r['training_input_sha256'] for r in logs[1]]
        assert all(r['update'] == i + 1 and r['finite_gradient_tensors'] == 104 and np.isfinite(r['loss']) for branch in logs for i, r in enumerate(branch))
        history = [load(out / f'seed{seed}_{condition}_history.json') for condition in ['paired_float_continuation', 'integer_forward_qat']]
        assert all(len(h) == 6 and h[-1]['updates'] == 120 for h in history)
        for h, log in zip(history, logs):
            for i in range(6): assert abs(h[i]['mean_loss'] - np.mean([r['loss'] for r in log[i*20:(i+1)*20]])) < 1e-12
        initial = torch.load(out / f'seed{seed}_initial_integer/state.pt', map_location='cpu', weights_only=True)
        admitted = torch.load(source['integer_initial_state'], map_location='cpu', weights_only=True)
        assert initial.keys() == admitted.keys() and all(torch.equal(initial[k], admitted[k]) for k in initial)
        floated = torch.load(out / f'seed{seed}_source_folded_fp32/state.pt', map_location='cpu', weights_only=True)
        for key, value in floated.items():
            ending = 'weight' if key.endswith('.weight') else 'bias'
            prefix = key[:-(len(ending)+1)]
            assert torch.equal(value, initial[prefix + '.conv.' + ending])
        qat = torch.load(out / f'seed{seed}_integer_forward_qat/state.pt', map_location='cpu', weights_only=True)
        parameter_keys = [k for k in initial if '.conv.' in k]
        buffer_keys = [k for k in initial if '.conv.' not in k]
        assert len(parameter_keys) == 104
        assert any(not torch.equal(qat[k], initial[k]) for k in parameter_keys)
        assert all(torch.equal(qat[k], initial[k]) for k in buffer_keys)
        float_final = torch.load(out / f'seed{seed}_paired_float_continuation/state.pt', map_location='cpu', weights_only=True)
        assert any(not torch.equal(float_final[k], floated[k]) for k in floated)
        pairs.append({'seed': seed, 'paired_steps': 120, 'augmented_input_hashes_identical': True,
                      'master_weight_initialization_equal': True, 'admitted_initial_state_exact': True,
                      'QAT_qparams_unchanged': True})
    ids = sorted({r['identity'] for r in gallery})
    checks = []
    runtime_forwards = numeric_conditions = 0
    for condition in summary['conditions']:
        seed, name = condition['seed'], condition['condition']
        directory = out / f'seed{seed}_{name}'
        assert sha(directory / 'packed.onnx') == condition['model_sha256']
        assert sha(directory / 'state.pt') == condition['state_sha256']
        vectors = np.load(directory / 'vectors.npz')
        if condition['quantized']:
            for runtime_name in ['OFF', 'ALL_disable_quant_qdq', 'ALL_default_diagnostic']:
                for i in range(8):
                    a, b = vectors['CPU'][i], vectors[runtime_name][i]
                    err = float(np.abs(a - b).max())
                    cosine = float(np.dot(a.astype(float), b.astype(float)) / (np.linalg.norm(a.astype(float)) * np.linalg.norm(b.astype(float))))
                    original = condition['export_gate']['rows'][i]['runtime'][runtime_name]
                    assert err == original['maximum_absolute_error'] and abs(cosine - original['cosine']) < 1e-12
                    assert (err <= .001 and cosine >= .9999) == original['pass']
                    if runtime_name != 'ALL_default_diagnostic': assert original['pass'] is True
                    numeric_conditions += 1
            assert float(np.max(np.abs(vectors['unpacked'] - vectors['OFF']))) <= 1e-6
        else:
            assert all(r['pass'] for r in condition['export_gate']['rows'])
            numeric_conditions += 8
        runtime_name = 'ALL_disable_quant_qdq' if condition['quantized'] else 'OFF'
        r = runtime(directory / 'packed.onnx', runtime_name)
        for i, x in enumerate(vectors['inputs']):
            assert np.array_equal(r.run(None, {'images': x[None]})[0], vectors[runtime_name][i:i+1])
            runtime_forwards += 1
        embeddings = np.load(directory / 'validation_embeddings.npz')
        g, q = embeddings['gallery'].astype(float), embeddings['queries'].astype(float)
        assert g.shape == (25, 576) and q.shape == (55, 576)
        pairwise = q @ g.T
        scores = np.stack([pairwise[:, [j for j, row in enumerate(gallery) if row['identity'] == identity]].max(1) for identity in ids], axis=1)
        choices = scores.argmax(1)
        best = scores[np.arange(len(queries)), choices]
        predicted = np.array([ids[i] for i in choices])
        known = np.array([row['identity'] in ids for row in queries])
        correct = predicted == np.array([row['identity'] for row in queries])
        assert int(known.sum()) == 25 and int((~known).sum()) == 30
        choices = []
        for threshold in sorted(set(best.tolist()) | {float(np.nextafter(best.max(), np.inf))}):
            accepted = best >= threshold
            unknown = int((accepted & ~known).sum())
            if unknown / 30 > .05 + 1e-12: continue
            C = int((accepted & known & correct).sum())
            W = int((accepted & known & ~correct).sum())
            choices.append(((C, -W, threshold), threshold))
        threshold = max(choices)[1]
        assert threshold == condition['threshold']['threshold']
        accepted = best >= threshold
        actual = {'known_queries': 25, 'unknown_queries': 30,
                  'known_correct_accepted_C': int((accepted & known & correct).sum()),
                  'known_wrong_accepted_W': int((accepted & known & ~correct).sum()),
                  'known_rejected_U': int((~accepted & known).sum()),
                  'known_closed_top1_correct': int((known & correct).sum()),
                  'unknown_false_accepts': int((accepted & ~known).sum())}
        for key, value in actual.items(): assert value == condition['validation'][key]
        predictions = load(directory / 'predictions.json')
        for row, identity, score, flag in zip(predictions, predicted, best, accepted):
            assert row['predicted_id'] == identity and abs(row['similarity'] - score) < 1e-12 and row['accepted'] == bool(flag)
        checks.append({'seed': seed, 'condition': name, 'threshold': threshold, **actual})
    assert len(checks) == 12 and runtime_forwards == 96
    result = {'status': 'PAIRED_UPDATES_INITIALIZATION_12_RETRIEVAL_CONDITIONS_AND_EXPORTS_INDEPENDENTLY_VERIFIED',
              'job_id': os.environ['SLURM_JOB_ID'], 'protocol_sha256': sha(ROOT / 'protocol/paired_integer_qat_v1.json'),
              'source_summary_sha256': sha(out / 'summary.json'), 'paired_controls': pairs,
              'conditions': checks, 'training_image_access_count': sum(r['split'] == 'train' for r in access),
              'validation_image_access_count': sum(r['split'].startswith('validation_') for r in access),
              'forbidden_old_evaluation_or_holdout_image_reads': 0,
              'numeric_metric_conditions': numeric_conditions, 'actual_runtime_regression_forwards': runtime_forwards,
              'formal_QAT_updates': 360, 'paired_float_updates': 360,
              'validation_calibration_and_scores_same_reused_queries': True,
              'FPGA_execution_verified': False, 'whole_goal_complete': False}
    target = ROOT / 'results/independent_verification.json'
    assert not target.exists()
    save = lambda path, value: Path(path).write_text(json.dumps(value, indent=2), encoding='utf-8')
    save(target, result)
    print(json.dumps(result), flush=True)


if __name__ == '__main__': main()
