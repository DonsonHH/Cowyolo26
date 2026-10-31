from pathlib import Path
from collections import Counter
import hashlib, json, os, tarfile
import numpy as np
import onnx
import onnxruntime as ort
PROJECT = Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT = PROJECT / 'integer_trainable_20261028'
assert os.environ.get('SLURM_JOB_ID') and __import__('socket').gethostname() != 'mu01'
check = json.loads((ROOT / 'results/independent_verification.json').read_text())
assert check['integer_accumulator_layer_cases'] == 2496
assert check['actual_discarded_smoke_updates'] == 6
assert not (ROOT / 'results/delivery.tar.gz').exists()
audit = []
for seed in [26, 27, 28]:
    for phase in ['initial', 'post2updates']:
        folder = ROOT / f'results/smoke_v2/seed{seed}_{phase}'
        model = onnx.load(folder / 'packed.onnx')
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        output = folder / 'actual_ALL_optimized.onnx'
        options.optimized_model_filepath = str(output)
        runtime = ort.InferenceSession(str(folder / 'packed.onnx'), sess_options=options, providers=['CPUExecutionProvider'])
        vectors = np.load(folder / 'vectors.npz')
        for i, x in enumerate(vectors['inputs']):
            assert np.array_equal(runtime.run(None, {'images': x[None]})[0], vectors['ALL_default_diagnostic'][i:i+1])
        optimized = onnx.load(output)
        audit.append({'seed': seed, 'phase': phase,
                      'packed_op_counts': dict(Counter(n.domain + ':' + n.op_type for n in model.graph.node)),
                      'actual_ALL_op_counts': dict(Counter(n.domain + ':' + n.op_type for n in optimized.graph.node)),
                      'serialized_ALL_graph_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                      'ALL_outputs_exactly_replayed': 8})
old = np.load(PROJECT / 'integer_reference_20261028/results/reference/whole_model_vectors.npz')
new = np.load(ROOT / 'results/smoke_v2/seed26_initial/vectors.npz')
assert np.array_equal(old['inputs'], new['inputs'])
graph_record = {'new_export_graph_audits': audit,
                'seed26_initial_CPU_vs_prior_integer_reference_max_difference': float(np.max(np.abs(new['CPU'] - old['reference']))),
                'initial_integer_candidate_graphs_not_the_old_default_failure_graph': True,
                'old_default_failure_graph_or_metrics_changed': False,
                'new_training_or_accuracy_claim': False}
(ROOT / 'results/export_graph_audit.json').write_text(json.dumps(graph_record, indent=2), encoding='utf-8')
paths = []
for folder in ['tools', 'protocol', 'results/smoke_v2', 'results/backward_probe']:
    paths.extend(p for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
paths.extend(p for p in (ROOT / 'logs').glob('*') if p.is_file() and not p.name.startswith('collect-' + os.environ['SLURM_JOB_ID']))
for seed in [26, 27, 28]:
    paths.extend(ROOT / f'results/smoke/seed{seed}_initial/{name}' for name in ['vectors.npz', 'summary.json'])
paths.extend(ROOT / p for p in ['results/smoke/progress.json', 'results/smoke/gradient_controls.json',
    'results/independent_verification.json', 'results/independent_feature_conditions.json',
    'results/export_graph_audit.json', '执行计划.md', 'smoke_job_id.txt', 'backward_probe_job_id.txt',
    'smoke_v2_job_id.txt', 'verify_job_id.txt'])
paths = sorted(set(paths))
manifest = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size,
             'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
manifest_path = ROOT / 'results/delivery_manifest.json'
manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
archive = ROOT / 'results/delivery.tar.gz'
with tarfile.open(archive, 'w:gz') as tf:
    for path in paths: tf.add(path, arcname=path.relative_to(ROOT).as_posix())
    tf.add(manifest_path, arcname='delivery_manifest.json')
record = {'manifest_files': len(manifest), 'archive_members': len(manifest) + 1,
          'bytes': archive.stat().st_size, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
          'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
          'old_failed_initial_duplicate_models_omitted_but_vectors_and_summaries_retained': True,
          'remote_old_failed_artifacts_deleted': False, 'running_collection_logs_excluded': True,
          'actual_discarded_smoke_updates': 6, 'formal_QAT_updates': 0, 'whole_goal_complete': False}
(ROOT / 'results/delivery_record.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print(json.dumps(record), flush=True)
