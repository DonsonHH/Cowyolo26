from pathlib import Path, PurePosixPath
import csv, hashlib, json, tarfile
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    record = json.loads((ROOT / 'results/delivery_record.json').read_text(encoding='utf-8'))
    archive_path = ROOT / 'results/delivery.tar.gz'
    assert archive_path.stat().st_size == record['bytes'] and sha(archive_path) == record['sha256']
    destination = ROOT / 'delivery'
    assert not destination.exists()
    with tarfile.open(archive_path, 'r:gz') as tf:
        members = tf.getmembers()
        assert len(members) == record['archive_file_members']
        assert all(m.isfile() for m in members)
        manifest_data = tf.extractfile('delivery_manifest.json').read()
        assert hashlib.sha256(manifest_data).hexdigest() == record['manifest_sha256']
        manifest = json.loads(manifest_data)
        assert len(manifest) == record['files_in_manifest']
        expected = {r['path']: r for r in manifest}
        assert len(expected) == len(manifest)
        assert {m.name for m in members} == set(expected) | {'delivery_manifest.json'}
        for member in members:
            name = PurePosixPath(member.name)
            assert not name.is_absolute() and '..' not in name.parts and ':' not in member.name
            path = destination.joinpath(*name.parts).resolve()
            assert path.is_relative_to(destination.resolve())
            payload = tf.extractfile(member).read()
            if member.name in expected:
                row = expected[member.name]
                assert len(payload) == row['bytes'] and hashlib.sha256(payload).hexdigest() == row['sha256']
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            assert sha(path) == hashlib.sha256(payload).hexdigest()
    folder = destination / 'results/reference'
    summary_path = folder / 'summary.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    checked = json.loads((destination / 'results/independent_verification.json').read_text(encoding='utf-8'))
    assert checked['source_summary_sha256'] == sha(summary_path)
    assert checked['independent_integer_layer_cases'] == checked['ORT_full_branch_exact_integer_cases'] == 416
    assert checked['accumulator_elements_recomputed'] == 11325248
    assert checked['equivalent_INT8_weight_elements'] == 912008
    assert checked['candidate_sha256'] == sha(folder / 'integer_accumulator_candidate.onnx')
    assert summary['protocol_sha256'] == sha(ROOT / 'protocol/integer_conv_v1.json')
    assert sha(ROOT / 'protocol/integer_conv_v1.json') == sha(destination / 'protocol/integer_conv_v1.json')
    for name in ['integer_math.py', 'run_reference.py', 'independent_verify.py']:
        assert sha(ROOT / 'tools' / name) == sha(destination / 'tools' / name)
    values = np.load(folder / 'whole_model_vectors.npz')
    old = np.load(ROOT.parent / 'qat_study_20261026/delivery/results/smoke/export_parity_vectors.npz')
    assert np.array_equal(values['inputs'], old['inputs'])
    results = []
    for i in range(8):
        row = {'vector': i,
               'old_QDQ_Torch_ORT_max_abs': float(np.max(np.abs(old['torch'][i] - old['packed'][i])))}
        for condition in ['ORT_disabled', 'ORT_default']:
            a, b = values['reference'][i], values[condition][i]
            error = float(np.max(np.abs(a - b)))
            cosine = float(np.dot(a.astype(float), b.astype(float)) / (np.linalg.norm(a.astype(float)) * np.linalg.norm(b.astype(float))))
            row[condition + '_max_abs'] = error
            row[condition + '_cosine'] = cosine
            row[condition + '_pass'] = error <= .001 and cosine >= .9999
        row['candidate_vs_old_QDQ_max_abs'] = float(np.max(np.abs(values['ORT_disabled'][i] - old['packed'][i])))
        results.append(row)
    assert sum(r['ORT_disabled_pass'] for r in results) == 8
    assert [r['vector'] for r in results if not r['ORT_default_pass']] == [2, 5]
    assert [r['vector'] for r in results if r['old_QDQ_Torch_ORT_max_abs'] > .001] == [3]
    csv_path = ROOT / 'results/eight_vector_numeric_comparison.csv'
    with csv_path.open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    log = (ROOT / 'results/status_04.txt').read_text(encoding='utf-8')
    for job in ['129976', '129977', '129978']:
        assert any(line.startswith(job + '|') and '|COMPLETED|0:0|' in line for line in log.splitlines())
    assert '129975|idcoo-intref|FAILED|1:0|' in log
    output = {'status': 'ALL35_DELIVERY_FILES_ARCHIVE_AND_LOCAL16_METRIC_CONDITIONS_VERIFIED',
              'archive_sha256': record['sha256'], 'bytes': record['bytes'], 'manifest_files': len(manifest),
              'local_metric_conditions': 16, 'old_failure_vector': 3,
              'candidate_disabled_passes': 8, 'candidate_default_passes': 6,
              'candidate_disabled_maximum_error': max(r['ORT_disabled_max_abs'] for r in results),
              'candidate_default_maximum_error': max(r['ORT_default_max_abs'] for r in results),
              'candidate_different_from_old_QDQ_vectors': [r['vector'] for r in results if r['candidate_vs_old_QDQ_max_abs'] > 0],
              'source_input_tensors_unchanged': True, 'training_updates': 0,
              'all_training_seeds_gradients_or_FPGA_verified': False, 'whole_goal_complete': False}
    target = ROOT / 'results/local_delivery_verification.json'
    assert not target.exists()
    target.write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(json.dumps(output))


if __name__ == '__main__':
    main()
