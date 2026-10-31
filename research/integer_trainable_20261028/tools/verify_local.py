from pathlib import Path, PurePosixPath
import csv, hashlib, json, tarfile
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    record = json.loads((ROOT / 'results/delivery_record.json').read_text())
    archive = ROOT / 'results/delivery.tar.gz'
    assert archive.stat().st_size == record['bytes'] and sha(archive) == record['sha256']
    destination = ROOT / 'delivery'
    assert not destination.exists()
    with tarfile.open(archive, 'r:gz') as tf:
        data = tf.extractfile('delivery_manifest.json').read()
        assert hashlib.sha256(data).hexdigest() == record['manifest_sha256']
        manifest = json.loads(data)
        expected = {r['path']: r for r in manifest}
        members = tf.getmembers()
        assert len(expected) == record['manifest_files'] == 82
        assert len(members) == record['archive_members'] == 83
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
    folder = destination / 'results/smoke_v2'
    summary = json.loads((folder / 'summary.json').read_text())
    independent = json.loads((destination / 'results/independent_verification.json').read_text())
    assert summary['status'] == 'ALL_THREE_TRAINABLE_INTEGER_SMOKE_GATES_PASS'
    assert independent['source_summary_sha256'] == sha(folder / 'summary.json')
    assert independent['integer_accumulator_layer_cases'] == 2496
    assert independent['accumulator_elements_recomputed'] == 67951488
    assert independent['runtime_metric_conditions'] == 144
    assert summary['actual_discarded_smoke_updates'] == 6 and summary['formal_QAT_updates'] == 0
    assert sha(ROOT / 'protocol/trainable_integer_smoke_v1.json') == summary['protocol_sha256']
    for name in ['integer_trainable.py', 'export_integer.py', 'smoke.py', 'smoke_v2.py', 'independent_verify.py']:
        assert sha(ROOT / 'tools' / name) == sha(destination / 'tools' / name)
    outputs, details = [], []
    previous = np.load(ROOT.parent / 'qat_study_20261026/delivery/results/smoke/export_parity_vectors.npz')
    for seed in summary['seeds']:
        assert seed['discarded_smoke_updates'] == 2 and seed['changed_parameter_tensors'] == 98
        assert len(seed['updates']) == 2 and all(r['finite_gradient_tensors'] == 104 for r in seed['updates'])
        for phase in ['initial', 'post2updates']:
            path = folder / f'seed{seed["seed"]}_{phase}'
            r = json.loads((path / 'summary.json').read_text())
            assert sha(path / 'packed.onnx') == r['packed_sha256'] and sha(path / 'state.pt') == r['state_sha256']
            assert r['packing']['packed_weight_arrays'] == 52 and r['packing']['packed_weight_bytes'] == 912008
            arrays = np.load(path / 'vectors.npz')
            assert np.array_equal(arrays['inputs'], previous['inputs'])
            maximum = {name: 0. for name in ['GPU', 'OFF', 'ALL_disable_quant_qdq', 'ALL_default_diagnostic']}
            for i in range(8):
                a = arrays['CPU'][i]
                for condition in maximum:
                    b = arrays[condition][i]
                    error = float(np.abs(a - b).max())
                    cosine = float(np.dot(a.astype(float), b.astype(float)) / (np.linalg.norm(a.astype(float)) * np.linalg.norm(b.astype(float))))
                    old = r['rows'][i]['GPU_CPU'] if condition == 'GPU' else r['rows'][i]['runtime'][condition]
                    assert error == old['maximum_absolute_error'] and abs(cosine - old['cosine']) < 1e-12
                    assert error <= .001 and cosine >= .9999 and old['pass'] is True
                    maximum[condition] = max(maximum[condition], error)
                    details.append({'seed': seed['seed'], 'phase': phase, 'vector': i,
                                    'condition': condition, 'maximum_absolute_error': error, 'cosine': cosine})
                assert float(np.max(np.abs(arrays['unpacked'][i] - arrays['OFF'][i]))) == r['rows'][i]['packing_max_error'] <= 1e-6
            outputs.append({'seed': seed['seed'], 'phase': phase, 'maximum_errors': maximum,
                            'packed_bytes': r['packing']['packed_bytes']})
    audit = json.loads((destination / 'results/export_graph_audit.json').read_text())
    assert len(audit['new_export_graph_audits']) == 6
    for row in audit['new_export_graph_audits']:
        assert row['ALL_outputs_exactly_replayed'] == 8
        path = folder / f'seed{row["seed"]}_{row["phase"]}/actual_ALL_optimized.onnx'
        assert row['serialized_ALL_graph_sha256'] == sha(path)
    csv_path = ROOT / 'results/forward_metrics192.csv'
    with csv_path.open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(details[0]))
        writer.writeheader()
        writer.writerows(details)
    report = {'status': 'ALL82_FILES_SIX_MODELS_AND192_FORWARD_METRICS_LOCALLY_VERIFIED',
              'files': 82, 'archive_sha256': record['sha256'], 'bytes': record['bytes'],
              'models': outputs, 'local_forward_metric_conditions': len(details), 'packing_checks': 48,
              'independent_integer_layer_cases': 2496, 'independent_accumulator_elements': 67951488,
              'actual_discarded_smoke_updates': 6, 'formal_QAT_updates': 0,
              'source_reference_feature_difference_retained': audit['seed26_initial_CPU_vs_prior_integer_reference_max_difference'],
              'new_local_model_forward': False, 'identity_accuracy_or_FPGA_verified': False,
              'whole_goal_complete': False}
    output = ROOT / 'results/local_verification.json'
    assert not output.exists()
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__': main()
