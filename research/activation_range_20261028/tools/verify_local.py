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
    with tarfile.open(archive, 'r:gz') as tf:
        raw = tf.extractfile('delivery_manifest.json').read()
        assert hashlib.sha256(raw).hexdigest() == rec['manifest_sha256']
        manifest = json.loads(raw)
        expected = {r['path']: r for r in manifest}
        members = tf.getmembers()
        assert len(expected) == rec['manifest_files'] and len(members) == rec['archive_members']
        assert {m.name for m in members} == set(expected) | {'delivery_manifest.json'}
        for member in members:
            name = PurePosixPath(member.name)
            assert member.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in member.name
            target = destination.joinpath(*name.parts).resolve()
            assert target.is_relative_to(destination.resolve())
            data = tf.extractfile(member).read()
            if member.name in expected:
                row = expected[member.name]
                assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256']
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                assert target.is_file() and sha(target) == hashlib.sha256(data).hexdigest()
            else:
                target.write_bytes(data)
            assert sha(target) == hashlib.sha256(data).hexdigest()
    folder = destination / 'results/probe'
    summary = load(folder / 'summary.json')
    checked = load(destination / 'results/independent_verification.json')
    assert checked['source_summary_sha256'] == sha(folder / 'summary.json')
    assert sha(ROOT / 'results/probe_summary.json') == sha(folder / 'summary.json')
    assert summary['protocol_sha256'] == sha(ROOT / 'protocol/activation_range_v1.json')
    assert checked['representative_integer_fixtures'] == 72 and checked['fixture_accumulator_elements_recomputed'] == 5682432
    assert checked['full_1872_layer_tensor_values_independently_replayed'] is False
    for name in ['probe.py', 'independent_verify.py']:
        assert sha(ROOT / 'tools' / name) == sha(destination / 'tools' / name)
    features = np.load(folder / 'feature_vectors.npz')
    data_rows = []
    MSE_reduction_errors = []
    for row in summary['conditions']:
        key = f'seed{row["seed"]}_{row["condition"]}_{row["view"]}'
        a, b = features[key].astype(float), features[f'seed{row["seed"]}_teacher_{row["view"]}'].astype(float)
        cosine = np.sum(a*b, axis=1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1))
        assert abs(float(cosine.mean()) - row['mean_teacher_cosine']) < 1e-12
        MSE_error = abs(float(np.mean((a-b)**2)) - row['mean_teacher_feature_MSE'])
        # Metricreduction auditonly. A measuredWindows/Linux lastbitdifference
        # doesnot alterthe separately frozenmodel exportfeature gate.
        assert MSE_error <= 1e-15
        MSE_reduction_errors.append(MSE_error)
        data_rows.append({**row, 'input_outside_percent': 100*row['weighted_input_outside_fraction'],
                          'output_outside_percent': 100*row['weighted_output_outside_fraction']})
    assert len(data_rows) == 36
    with (ROOT / 'results/conditions36.csv').open('w', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(data_rows[0]))
        writer.writeheader()
        writer.writerows(data_rows)
    layers = load(folder / 'layer_statistics.json')
    top = []
    for seed in [26, 27, 28]:
        for view in ['deterministic', 'augmented']:
            eligible = [r for r in layers if r['seed'] == seed and r['view'] == view and r['condition'] == 'integer_forward_qat']
            assert len(eligible) == 52
            top.extend(sorted(eligible, key=lambda r: (-r['output_outside_fraction'], r['layer_index']))[:5])
    (ROOT / 'results/QAT_top5_output_ranges_each_view.json').write_text(json.dumps(top, indent=2), encoding='utf-8')
    status = (ROOT / 'results/delivery_status_01.txt').read_text(encoding='utf-8')
    for job in ['130003', '130004', '130005']:
        assert any(line.startswith(job + '|') and '|COMPLETED|0:0|' in line for line in status.splitlines())
    assert len(checked['counterfactual_effects']) == 12 and all(r['mean_teacher_cosine_difference'] < 0 for r in checked['counterfactual_effects'])
    selected = [r for r in data_rows if r['condition'] in ['integer_forward_qat', 'QAT_no_activation_clipping', 'QAT_no_weight_clipping']]
    report = {'status': 'ALL_RANGE_DELIVERY_FILES_36_FEATURE_METRICS_AND_CONTROL_SIGNS_LOCALLY_VERIFIED',
              'files': len(manifest), 'bytes': rec['bytes'], 'archive_sha256': rec['sha256'],
              'feature_metric_conditions': 36, 'weighted_clip_count_rows': 1872,
              'representative_arithmetic_fixtures': 72,
              'representative_accumulator_elements': 5682432,
              'all12_unclipping_controls_lower_mean_teacher_cosine': True,
              'maximum_local_MSE_reduction_difference': max(MSE_reduction_errors),
              'metric_reduction_audit_absolute_tolerance': 1e-15,
              'model_export_gate_tolerances_changed': False,
              'QAT_and_counterfactual_rows': selected,
              'new_training_updates': 0, 'validation_or_test_reads': 0,
              'counterfactuals_are_not_deployable_UINT8_INT8': True,
              'FPGA_execution_verified': False, 'whole_goal_complete': False}
    path = ROOT / 'results/local_verification.json'
    assert not path.exists()
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'QAT_and_counterfactual_rows'}))
    print(json.dumps({'QAT': [r for r in data_rows if r['condition'] == 'integer_forward_qat'],
                      'worst_QAT_layer_fractions': [{'seed': r['seed'], 'view': r['view'], 'module': r['module'],
                          'output_outside_percent': 100*r['output_outside_fraction'], 'output_elements': r['output_elements']} for r in top[::5]]}))


if __name__ == '__main__': main()
