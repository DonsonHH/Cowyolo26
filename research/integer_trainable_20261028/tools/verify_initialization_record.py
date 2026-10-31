from pathlib import Path
import hashlib, json
ROOT = Path(__file__).resolve().parents[1]
path = ROOT / 'results/initialization_probe.json'
digest = hashlib.sha256(path.read_bytes()).hexdigest()
assert digest == '67b8bec180e522e0efb24ad3b77f29e1941711fb34cb2c4fb597a6a3c4806623'
d = json.loads(path.read_text())
assert len(d['layers']) == d['old_GPU_fold_weight_exact_layers'] == d['old_GPU_fold_bias_exact_layers'] == 52
assert all(r['new_state_exact_CPU_fold_weights_bias'] and r['old_graph_exact_GPU_fold_weights'] and r['old_graph_exact_GPU_fold_bias'] for r in d['layers'])
assert sum(r['CPU_GPU_weight_different_elements'] for r in d['layers']) == d['CPU_GPU_weight_different_elements'] == 128707
assert sum(r['new_vs_old_weight_code_different_elements'] for r in d['layers']) == d['changed_quantized_weight_elements'] == 6
assert sum(any(v['different_elements'] for v in r['qparam_differences'].values()) for r in d['layers']) == d['layers_with_quantizer_parameter_differences'] == 49
assert d['seed26_new_old_feature_maximum_difference'] == .02865108847618103
assert d['source_checkpoint_and_input_tensors_unchanged'] is True
status = (ROOT / 'results/initialization_status_01.txt').read_text()
assert '129994|idcoo-int-init-check|COMPLETED|0:0|' in status
result = {'status': 'INITIALIZATION_PROBE_HASH_ARITHMETIC_AND_TERMINAL_STATE_VERIFIED',
          'source_sha256': digest, 'old_all52_layers_exact_GPU_fold': True,
          'new_all52_layers_exact_CPU_fold': True, 'quantized_weight_differences': 6,
          'layers_with_qparam_differences': 49, 'new_old_feature_difference': d['seed26_new_old_feature_maximum_difference'],
          'old_new_candidate_not_identical': True, 'no_new_training': True}
(ROOT / 'results/initialization_local_verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
