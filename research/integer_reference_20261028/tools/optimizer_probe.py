from pathlib import Path
from collections import Counter
import copy, hashlib, json, os, time
import numpy as np
import onnx
from onnx import helper
import onnxruntime as ort

ROOT = Path('/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2), encoding='utf-8')


def session(model, level, export=None):
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    options.graph_optimization_level = getattr(ort.GraphOptimizationLevel, {
        'OFF': 'ORT_DISABLE_ALL', 'BASIC': 'ORT_ENABLE_BASIC',
        'EXTENDED': 'ORT_ENABLE_EXTENDED', 'ALL': 'ORT_ENABLE_ALL'}[level])
    if export is not None:
        options.optimized_model_filepath = str(export)
    return ort.InferenceSession(model, sess_options=options, providers=['CPUExecutionProvider'])


def metric(reference, candidate):
    a, b = reference.astype(np.float64), candidate.astype(np.float64)
    error = float(np.max(np.abs(reference - candidate)))
    cosine = float(np.sum(a * b) / (np.linalg.norm(a) * np.linalg.norm(b)))
    return {'maximum_absolute_error': error, 'cosine': cosine,
            'passed_original_embedding_tolerance': error <= .001 and cosine >= .9999}


def node_record(node):
    return {'name': node.name, 'domain': node.domain, 'op_type': node.op_type,
            'inputs': list(node.input), 'outputs': list(node.output)}


def augment(graph, outputs, metadata):
    result = copy.deepcopy(graph)
    existing = {v.name for v in result.graph.output}
    result.graph.output.extend([copy.deepcopy(metadata[name]) for name in outputs if name not in existing])
    return result


def main():
    assert os.environ.get('SLURM_JOB_ID') and __import__('socket').gethostname() != 'mu01'
    protocol_path = ROOT / 'protocol/optimizer_probe_v1.json'
    p = json.loads(protocol_path.read_text())
    assert ort.__version__ == p['ORT_version']
    for row in p['inputs']:
        assert sha(row['remote_path']) == row['sha256']
    out = ROOT / 'results/optimizer_probe'
    out.mkdir(exist_ok=False)
    start = time.perf_counter()
    source = ROOT / 'results/reference/integer_accumulator_candidate.onnx'
    vectors = np.load(ROOT / 'results/reference/whole_model_vectors.npz')
    old_summary = json.loads((ROOT / 'results/reference/summary.json').read_text())
    assert old_summary['candidate_passed_vectors'] == 8 and old_summary['candidate_default_passed_vectors'] == 6
    conditions, outputs, snapshots = [], {}, {}
    for level in p['levels']:
        snapshot = out / f'actual_optimized_{level}.onnx'
        runtime = session(str(source), level, snapshot)
        values = []
        for i, x in enumerate(vectors['inputs']):
            z = runtime.run(None, {'images': x[None]})[0]
            if level in ['OFF', 'ALL']:
                assert np.array_equal(z, vectors['ORT_disabled' if level == 'OFF' else 'ORT_default'][i:i+1])
            conditions.append({'level': level, 'vector': i, **metric(vectors['reference'][i:i+1], z)})
            values.append(z)
        outputs[level] = np.concatenate(values)
        snapshots[level] = {'file': snapshot.name, 'sha256': sha(snapshot)}
        print(json.dumps({'event': 'OPTIMIZATION_LEVEL', 'level': level,
                          'passed': sum(r['passed_original_embedding_tolerance'] for r in conditions if r['level'] == level)}), flush=True)
    optimized = onnx.load(out / 'actual_optimized_ALL.onnx')
    replay = session(str(out / 'actual_optimized_ALL.onnx'), 'OFF')
    replay_rows = []
    for i, x in enumerate(vectors['inputs']):
        actual = replay.run(None, {'images': x[None]})[0]
        assert np.array_equal(actual, outputs['ALL'][i:i+1])
        replay_rows.append({'vector': i, 'serialized_replay_exact_original_ALL': True})
    original = onnx.load(source)
    source_producers = {v: n for n in original.graph.node for v in n.output}
    opt_producers = {v: n for n in optimized.graph.node for v in n.output}
    typed = onnx.shape_inference.infer_shapes(original)
    metadata = {v.name: v for v in list(typed.graph.value_info) + list(typed.graph.input) + list(typed.graph.output)}
    common = [v for n in original.graph.node for v in n.output if v in opt_producers and v in metadata]
    assert len(common) == len(set(common)) and 'embedding' in common
    original_probe = session(augment(original, common, metadata).SerializeToString(), 'OFF')
    optimized_probe = session(augment(optimized, common, metadata).SerializeToString(), 'OFF')
    original_names = [v.name for v in original_probe.get_outputs()]
    opt_names = [v.name for v in optimized_probe.get_outputs()]
    traces, firsts, tensors, preservation = [], [], {}, []
    for i in p['trace_vectors']:
        x = vectors['inputs'][i:i+1]
        a = dict(zip(original_names, original_probe.run(None, {'images': x})))
        b = dict(zip(opt_names, optimized_probe.run(None, {'images': x})))
        assert np.array_equal(a['embedding'], outputs['OFF'][i:i+1])
        assert np.array_equal(b['embedding'], outputs['ALL'][i:i+1])
        preservation.append({'vector': i, 'original_embedding_unchanged_after_trace_outputs': True,
                             'serialized_ALL_embedding_unchanged_after_trace_outputs': True})
        different = []
        for position, name in enumerate(common):
            aa, bb = a[name], b[name]
            assert aa.dtype == bb.dtype and aa.shape == bb.shape
            finite = bool(np.isfinite(aa).all() and np.isfinite(bb).all())
            assert finite
            differences = aa.astype(np.float64) - bb.astype(np.float64)
            row = {'vector': i, 'source_order': position, 'tensor': name, 'dtype': str(aa.dtype),
                   'shape': list(aa.shape), 'different_elements': int(np.count_nonzero(aa != bb)),
                   'maximum_absolute_error': float(np.max(np.abs(differences))) if aa.size else 0.,
                   'source_producer': node_record(source_producers[name]), 'optimized_producer': node_record(opt_producers[name])}
            traces.append(row)
            if row['different_elements']:
                different.append(row)
        assert different
        first = different[0]
        integer = next((r for r in different if np.issubdtype(a[r['tensor']].dtype, np.integer)), None)
        entry = {'vector': i, 'first_common_difference': first, 'first_common_integer_difference': integer,
                 'all_different_common_tensors': len(different), 'common_tensors': len(common)}
        for label, selected in [('first', first), ('first_integer', integer)]:
            if selected is None:
                continue
            name = selected['tensor']
            tensors[f'v{i}_{label}_OFF'] = a[name]
            tensors[f'v{i}_{label}_ALL'] = b[name]
            for j, input_name in enumerate(source_producers[name].input):
                if input_name in a and input_name in b:
                    tensors[f'v{i}_{label}_input{j}_OFF'] = a[input_name]
                    tensors[f'v{i}_{label}_input{j}_ALL'] = b[input_name]
        firsts.append(entry)
        print(json.dumps({'event': 'FIRST_COMMON_DIVERGENCE', **entry}), flush=True)
    np.savez_compressed(out / 'level_embeddings.npz', inputs=vectors['inputs'], reference=vectors['reference'], **outputs)
    np.savez_compressed(out / 'first_divergence_tensors.npz', **tensors)
    save(out / 'metric_conditions.json', conditions)
    save(out / 'common_tensor_trace.json', traces)
    save(out / 'first_divergences.json', firsts)
    structure = {'original_nodes': len(original.graph.node), 'optimized_nodes': len(optimized.graph.node),
                 'original_ops': dict(Counter((n.domain + ':' + n.op_type) for n in original.graph.node)),
                 'optimized_ops': dict(Counter((n.domain + ':' + n.op_type) for n in optimized.graph.node)),
                 'common_typed_tensors': common}
    save(out / 'graph_structure.json', structure)
    summary = {'status': 'ACTUAL_OPTIMIZED_GRAPH_EXACT_REPLAY_AND_FIRST_DIVERGENCES_CAPTURED',
               'job_id': os.environ['SLURM_JOB_ID'], 'protocol_sha256': sha(protocol_path),
               'source_candidate_sha256': sha(source), 'snapshots': snapshots,
               'levels_passed': {level: sum(r['passed_original_embedding_tolerance'] for r in conditions if r['level'] == level) for level in p['levels']},
               'prior_OFF_ALL_outputs_exactly_reproduced': True, 'serialized_ALL_replay_vectors': replay_rows,
               'common_tensors_per_traced_vector': len(common), 'tracing_preservation_checks': preservation,
               'first_divergences': firsts, 'specific_causal_transformer_proven': False,
               'new_training_updates': 0, 'new_image_reads': 0, 'FPGA_execution': False,
               'elapsed_s': time.perf_counter() - start, 'whole_goal_complete': False}
    save(out / 'summary.json', summary)
    print(json.dumps({'status': summary['status'], 'levels_passed': summary['levels_passed'],
                      'original_nodes': structure['original_nodes'], 'optimized_nodes': structure['optimized_nodes'],
                      'common_tensors': len(common), 'elapsed_s': summary['elapsed_s']}), flush=True)


if __name__ == '__main__':
    main()
