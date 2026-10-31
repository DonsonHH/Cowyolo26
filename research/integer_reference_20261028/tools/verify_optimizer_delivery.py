from pathlib import Path, PurePosixPath
import csv, hashlib, json, tarfile
import numpy as np
ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    record = json.loads((ROOT / 'results/optimizer_delivery_record.json').read_text(encoding='utf-8'))
    archive = ROOT / 'results/optimizer_delivery.tar.gz'
    assert archive.stat().st_size == record['bytes'] and sha(archive) == record['sha256']
    destination = ROOT / 'optimizer_delivery'
    assert not destination.exists()
    with tarfile.open(archive, 'r:gz') as tf:
        members = tf.getmembers()
        payload = tf.extractfile('optimizer_delivery_manifest.json').read()
        assert hashlib.sha256(payload).hexdigest() == record['manifest_sha256']
        manifest = json.loads(payload)
        expected = {r['path']: r for r in manifest}
        assert len(expected) == record['manifest_files'] == 43
        assert len(members) == record['archive_members'] == 44
        assert {m.name for m in members} == set(expected) | {'optimizer_delivery_manifest.json'}
        for member in members:
            name = PurePosixPath(member.name)
            assert member.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in member.name
            path = destination.joinpath(*name.parts).resolve()
            assert path.is_relative_to(destination.resolve())
            data = tf.extractfile(member).read()
            if member.name in expected:
                row = expected[member.name]
                assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            assert sha(path) == hashlib.sha256(data).hexdigest()
    probe = destination / 'results/optimizer_probe'
    isolated = destination / 'results/optimizer_isolation'
    checked_path = destination / 'results/optimizer_independent_verification.json'
    checked = json.loads(checked_path.read_text(encoding='utf-8'))
    assert checked['probe_summary_sha256'] == sha(probe / 'summary.json')
    assert checked['isolation_summary_sha256'] == sha(isolated / 'summary.json')
    assert sha(ROOT / 'results/optimizer_probe_summary.json') == sha(probe / 'summary.json')
    assert sha(ROOT / 'results/optimizer_first_divergences.json') == sha(probe / 'first_divergences.json')
    assert checked['single_existing_node_changed'] is True
    assert checked['all_other_nodes_and_initializers_unchanged'] is True
    assert checked['metric_conditions'] == 48 and checked['original_typed_common_tensor_rows'] == 1060
    assert checked['isolated_mismatch_vectors'] == [2, 5, 7]
    assert checked['both_controlled_paths_exact_OFF_output'] is True
    for name in ['optimizer_probe.py', 'isolate_optimizer_add.py', 'verify_optimizer_controls.py']:
        assert sha(ROOT / 'tools' / name) == sha(destination / 'tools' / name)
    for name in ['optimizer_probe_v1.json', 'optimizer_isolation_v1.json']:
        assert sha(ROOT / 'protocol' / name) == sha(destination / 'protocol' / name)
    p = json.loads((probe / 'summary.json').read_text(encoding='utf-8'))
    for snapshot in p['snapshots'].values():
        assert snapshot['sha256'] == sha(probe / snapshot['file'])
    levels = np.load(probe / 'level_embeddings.npz')
    controls = np.load(isolated / 'controlled_embeddings.npz')
    baseline = np.load(ROOT / 'delivery/results/reference/whole_model_vectors.npz')
    assert np.array_equal(levels['inputs'], controls['inputs']) and np.array_equal(levels['inputs'], baseline['inputs'])
    primary = {(r['level'], r['vector']): r for r in json.loads((probe / 'metric_conditions.json').read_text(encoding='utf-8'))}
    records = json.loads((isolated / 'records.json').read_text(encoding='utf-8'))
    for row in records:
        primary[('patched', row['vector'])] = row['patched_one_node']
        primary[('ALL_disable_quant_qdq', row['vector'])] = row['disable_quant_qdq']
    independent = {(r['condition'], r['vector']): r for r in json.loads((destination / 'results/optimizer_independent_metrics.json').read_text(encoding='utf-8'))}
    metrics, passed = [], {}
    for condition in ['OFF', 'BASIC', 'EXTENDED', 'ALL', 'patched', 'ALL_disable_quant_qdq']:
        output = levels[condition] if condition in levels.files else controls[condition]
        passed[condition] = 0
        for i in range(8):
            a, b = levels['reference'][i].astype(float), output[i].astype(float)
            error = float(np.max(np.abs(levels['reference'][i] - output[i])))
            cosine = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
            ok = error <= .001 and cosine >= .9999
            first = primary[condition, i]
            second = independent[condition, i]
            assert error == first['maximum_absolute_error'] == second['maximum_absolute_error']
            assert abs(cosine - first['cosine']) < 1e-12 and abs(cosine - second['cosine']) < 1e-12
            assert ok == first['passed_original_embedding_tolerance'] == second['passed']
            metrics.append({'condition': condition, 'vector': i, 'max_absolute_error': error, 'cosine': cosine, 'pass': ok})
            passed[condition] += int(ok)
    assert passed == checked['pass_counts']
    assert np.array_equal(controls['patched'], levels['OFF'])
    assert np.array_equal(controls['ALL_disable_quant_qdq'], levels['OFF'])
    node_tensors = np.load(isolated / 'isolated_node_vectors.npz')
    counts = {i: int(np.count_nonzero(node_tensors[f'v{i}_fused'] != node_tensors[f'v{i}_unfused'])) for i in range(8)}
    assert counts == {0: 0, 1: 0, 2: 1, 3: 0, 4: 0, 5: 1, 6: 0, 7: 1}
    assert np.array_equal(levels['ALL'][7], levels['OFF'][7])
    status = (ROOT / 'results/optimizer_delivery_status_01.txt').read_text(encoding='utf-8')
    for job in ['129981', '129982', '129983', '129984']:
        assert any(line.startswith(job + '|') and '|COMPLETED|0:0|' in line for line in status.splitlines())
    csv_path = ROOT / 'results/optimizer48_metrics.csv'
    with csv_path.open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(metrics[0]))
        writer.writeheader()
        writer.writerows(metrics)
    output = {'status': 'ALL43_OPTIMIZER_DELIVERY_FILES_AND48_NUMERIC_CONDITIONS_LOCALLY_VERIFIED',
              'archive_sha256': record['sha256'], 'bytes': record['bytes'], 'files': 43,
              'metric_conditions': len(metrics), 'pass_counts': passed,
              'local_operator_mismatch_counts': counts,
              'source_input_tensors_unchanged': True,
              'patched_and_no_QDQ_fusion_exact_OFF_output': True,
              'new_local_model_forward_performed': False,
              'new_training_updates': 0, 'all_seeds_gradients_or_FPGA_verified': False,
              'whole_goal_complete': False}
    path = ROOT / 'results/optimizer_local_verification.json'
    assert not path.exists()
    path.write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(json.dumps(output))


if __name__ == '__main__':
    main()
