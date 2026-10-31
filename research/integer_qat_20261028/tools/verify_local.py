from pathlib import Path, PurePosixPath
import csv, hashlib, json, tarfile
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    rec = load(ROOT / 'results/delivery_record.json')
    archive = ROOT / 'results/delivery.tar.gz'
    assert archive.stat().st_size == rec['bytes'] and sha(archive) == rec['sha256']
    destination = ROOT / 'delivery'
    assert not destination.exists()
    with tarfile.open(archive, 'r:gz') as tf:
        data = tf.extractfile('delivery_manifest.json').read()
        assert hashlib.sha256(data).hexdigest() == rec['manifest_sha256']
        manifest = json.loads(data)
        expected = {r['path']: r for r in manifest}
        members = tf.getmembers()
        assert len(expected) == rec['manifest_files'] and len(members) == rec['archive_members']
        assert {m.name for m in members} == set(expected) | {'delivery_manifest.json'}
        for member in members:
            name = PurePosixPath(member.name)
            assert member.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in member.name
            target = destination.joinpath(*name.parts).resolve()
            assert target.is_relative_to(destination.resolve())
            payload = tf.extractfile(member).read()
            if member.name in expected:
                row = expected[member.name]
                assert len(payload) == row['bytes'] and hashlib.sha256(payload).hexdigest() == row['sha256']
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            assert sha(target) == hashlib.sha256(payload).hexdigest()
    folder = destination / 'results/study'
    summary = load(folder / 'summary.json')
    verification = load(destination / 'results/independent_verification.json')
    assert verification['source_summary_sha256'] == sha(folder / 'summary.json')
    assert summary['protocol_sha256'] == sha(ROOT / 'protocol/paired_integer_qat_v1.json')
    assert summary['formal_QAT_updates'] == summary['paired_float_updates'] == 360
    assert verification['actual_runtime_regression_forwards'] == 96
    assert summary['freeze_sha256'] == sha(folder / 'all_models_thresholds_frozen.json')
    for name in ['train.py', 'independent_verify.py']:
        assert sha(ROOT / 'tools' / name) == sha(destination / 'tools' / name)
    results = []
    index = load(folder / 'validation_index.json')
    for condition in summary['conditions']:
        seed, name = condition['seed'], condition['condition']
        path = folder / f'seed{seed}_{name}'
        assert sha(path / 'packed.onnx') == condition['model_sha256']
        assert sha(path / 'state.pt') == condition['state_sha256']
        embeddings = np.load(path / 'validation_embeddings.npz')
        gallery, queries = embeddings['gallery'].astype(float), embeddings['queries'].astype(float)
        ids = sorted({r['identity'] for r in index['gallery']})
        pairwise = queries @ gallery.T
        scores = np.stack([pairwise[:, [j for j, r in enumerate(index['gallery']) if r['identity'] == identity]].max(1) for identity in ids], axis=1)
        choices = scores.argmax(1)
        predicted = np.array([ids[i] for i in choices])
        best = scores[np.arange(55), choices]
        known = np.array([r['identity'] in ids for r in index['queries']])
        correct = predicted == np.array([r['identity'] for r in index['queries']])
        threshold = condition['threshold']['threshold']
        accepted = best >= threshold
        candidates = []
        for value in np.unique(np.append(best, np.nextafter(best.max(), np.inf))):
            take = best >= value
            if int((take & ~known).sum()) > 1: continue
            candidates.append((int((take & known & correct).sum()), -int((take & known & ~correct).sum()), float(value)))
        assert max(candidates)[2] == threshold
        actual = {'C': int((accepted & known & correct).sum()), 'W': int((accepted & known & ~correct).sum()),
                  'U': int((~accepted & known).sum()), 'closed_top1': int((known & correct).sum()),
                  'unknown_false_accepts': int((accepted & ~known).sum())}
        assert actual['C'] + actual['W'] + actual['U'] == 25 and int((~known).sum()) == 30
        for local, key in [('C', 'known_correct_accepted_C'), ('W', 'known_wrong_accepted_W'),
                           ('U', 'known_rejected_U'), ('closed_top1', 'known_closed_top1_correct'),
                           ('unknown_false_accepts', 'unknown_false_accepts')]:
            assert actual[local] == condition['validation'][key]
        results.append({'seed': seed, 'condition': name, **actual, 'threshold': threshold})
    assert len(results) == 12
    for seed in [26, 27, 28]:
        a, b = [load(folder / f'seed{seed}_{condition}_batches.json') for condition in ['paired_float_continuation', 'integer_forward_qat']]
        assert len(a) == len(b) == 120
        assert [r['training_input_sha256'] for r in a] == [r['training_input_sha256'] for r in b]
        assert all(r['finite_gradient_tensors'] == 104 for r in a + b)
    with (ROOT / 'results/validation12_conditions.csv').open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    result = {'status': 'ALL_PAIRED_QAT_DELIVERY_FILES_AND12_VALIDATION_CONDITIONS_LOCALLY_VERIFIED',
              'files': len(manifest), 'bytes': rec['bytes'], 'archive_sha256': rec['sha256'],
              'validation_conditions': results, 'paired_augmented_steps_verified': 360,
              'formal_QAT_updates': 360, 'paired_float_updates': 360,
              'source_input_roles_and_independent_verification_bound': True,
              'validation_reused_calibration_queries': True, 'FPGA_execution_verified': False,
              'whole_goal_complete': False}
    path = ROOT / 'results/local_verification.json'
    assert not path.exists()
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__': main()
