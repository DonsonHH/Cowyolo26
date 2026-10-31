from pathlib import Path
import hashlib, json
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / 'delivery/results/probe'
summary = json.loads((folder / 'summary.json').read_text())
features = np.load(folder / 'feature_vectors.npz')
rows = []
for row in summary['conditions']:
    key = f'seed{row["seed"]}_{row["condition"]}_{row["view"]}'
    a = features[key].astype(float)
    b = features[f'seed{row["seed"]}_teacher_{row["view"]}'].astype(float)
    actual = float(np.mean((a-b)**2))
    previous = row['mean_teacher_feature_MSE']
    rows.append({'seed': row['seed'], 'condition': row['condition'], 'view': row['view'],
                 'saved_MSE': previous, 'local_MSE': actual, 'absolute_difference': abs(actual-previous)})
output = {'status': 'LOCAL_MEAN_REDUCTION_ROUNDING_MEASURED', 'conditions': 36,
          'different_lastbit_conditions': sum(r['absolute_difference'] > 0 for r in rows),
          'maximum_absolute_MSE_reduction_difference': max(r['absolute_difference'] for r in rows),
          'model_arrays_changed': False, 'model_embedding_gate_changed': False, 'rows': rows}
path = ROOT / 'results/local_metric_rounding_probe.json'
assert not path.exists()
path.write_text(json.dumps(output, indent=2), encoding='utf-8')
before = ROOT / 'tools/verify_local.py'
backup = ROOT / 'tools/verify_local_before_metric_tolerance.py'
assert not backup.exists()
backup.write_bytes(before.read_bytes())
print(json.dumps({k: v for k, v in output.items() if k != 'rows'}))
