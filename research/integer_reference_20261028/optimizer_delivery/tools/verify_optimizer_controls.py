from pathlib import Path
import hashlib, json, os
import numpy as np
import onnx
from onnx import numpy_helper
import onnxruntime as ort

ROOT = Path('/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def runtime(path):
    option = ort.SessionOptions()
    option.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
    option.intra_op_num_threads = 2
    option.inter_op_num_threads = 1
    return ort.InferenceSession(str(path), sess_options=option, providers=['CPUExecutionProvider'])


def main():
    assert os.environ.get('SLURM_JOB_ID') and __import__('socket').gethostname() != 'mu01'
    probe = ROOT / 'results/optimizer_probe'
    isolated = ROOT / 'results/optimizer_isolation'
    p = json.loads((probe / 'summary.json').read_text())
    s = json.loads((isolated / 'summary.json').read_text())
    assert p['protocol_sha256'] == sha(ROOT / 'protocol/optimizer_probe_v1.json')
    assert s['protocol_sha256'] == sha(ROOT / 'protocol/optimizer_isolation_v1.json')
    assert p['snapshots']['ALL']['sha256'] == s['source_serialized_ALL_sha256'] == sha(probe / 'actual_optimized_ALL.onnx')
    source = onnx.load(probe / 'actual_optimized_ALL.onnx')
    patched = onnx.load(isolated / 'serialized_ALL_one_Add_restored.onnx')
    index = next(i for i, n in enumerate(source.graph.node) if n.name == s['target_node']['name'])
    original_node = source.graph.node[index]
    assert original_node.op_type == 'QLinearAdd' and original_node.domain == 'com.microsoft'
    assert len(patched.graph.node) == len(source.graph.node) + 3
    assert [n.SerializeToString() for n in source.graph.node[:index]] == [n.SerializeToString() for n in patched.graph.node[:index]]
    assert [n.SerializeToString() for n in source.graph.node[index+1:]] == [n.SerializeToString() for n in patched.graph.node[index+4:]]
    assert [v.SerializeToString() for v in source.graph.initializer] == [v.SerializeToString() for v in patched.graph.initializer]
    restored_nodes = list(patched.graph.node[index:index+4])
    assert [n.op_type for n in restored_nodes] == ['DequantizeLinear', 'DequantizeLinear', 'Add', 'QuantizeLinear']
    assert list(restored_nodes[0].input) == list(original_node.input[:3])
    assert list(restored_nodes[1].input) == list(original_node.input[3:6])
    assert list(restored_nodes[3].input[1:]) == list(original_node.input[6:])
    assert list(restored_nodes[3].output) == list(original_node.output)
    arrays = {v.name: numpy_helper.to_array(v) for v in source.graph.initializer}
    sa, za, sb, zb, sy, zy = [np.asarray(arrays[original_node.input[j]]).reshape(()) for j in [1, 2, 4, 5, 6, 7]]
    tensors = np.load(isolated / 'isolated_node_vectors.npz')
    fused = runtime(isolated / 'isolated_QLinearAdd.onnx')
    plain = runtime(isolated / 'isolated_DQ_Add_Q.onnx')
    records = json.loads((isolated / 'records.json').read_text())
    mismatch_vectors = []
    scalar_cases = []
    for i in range(8):
        a, b = tensors[f'v{i}_A'], tensors[f'v{i}_B']
        feed = {original_node.input[0]: a, original_node.input[3]: b}
        fq = fused.run(None, feed)[0]
        uq = plain.run(None, feed)[0]
        assert np.array_equal(fq, tensors[f'v{i}_fused'])
        assert np.array_equal(uq, tensors[f'v{i}_unfused'])
        raw_a = (a.astype(np.float32) - np.float32(za)) * np.float32(sa)
        raw_b = (b.astype(np.float32) - np.float32(zb)) * np.float32(sb)
        q = np.clip(np.rint((raw_a + raw_b) / np.float32(sy)) + np.float32(zy), 0, 255).astype(np.uint8)
        assert np.array_equal(q, uq)
        points = np.argwhere(fq != uq)
        assert len(points) == records[i]['isolated_output_different_elements']
        if len(points):
            mismatch_vectors.append(i)
        for position in points:
            key = tuple(position)
            predicted = float(((np.float32(int(a[key])) - np.float32(za)) * np.float32(sa)
                               + (np.float32(int(b[key])) - np.float32(zb)) * np.float32(sb)) / np.float32(sy))
            assert int(a[key]) == 152 and int(b[key]) == 180
            assert int(fq[key]) == 172 and int(uq[key]) == 171
            scalar_cases.append({'vector': i, 'index': position.tolist(), 'A': int(a[key]), 'B': int(b[key]),
                                 'unfused_FP32_units': predicted, 'fused_U8': 172, 'unfused_U8': 171})
    assert mismatch_vectors == [2, 5, 7]
    levels = np.load(probe / 'level_embeddings.npz')
    controls = np.load(isolated / 'controlled_embeddings.npz')
    assert np.array_equal(levels['inputs'], controls['inputs'])
    metrics = []
    passed = {}
    for name in ['OFF', 'BASIC', 'EXTENDED', 'ALL', 'patched', 'ALL_disable_quant_qdq']:
        values = levels[name] if name in levels.files else controls[name]
        passed[name] = 0
        for i in range(8):
            ref = levels['reference'][i].astype(np.float64)
            value = values[i].astype(np.float64)
            err = float(np.max(np.abs(levels['reference'][i] - values[i])))
            cos = float(np.dot(ref, value) / (np.linalg.norm(ref) * np.linalg.norm(value)))
            ok = err <= .001 and cos >= .9999
            passed[name] += int(ok)
            metrics.append({'condition': name, 'vector': i, 'maximum_absolute_error': err, 'cosine': cos, 'passed': ok})
    assert passed == {'OFF': 8, 'BASIC': 8, 'EXTENDED': 6, 'ALL': 6, 'patched': 8, 'ALL_disable_quant_qdq': 8}
    assert np.array_equal(controls['patched'], levels['OFF'])
    assert np.array_equal(controls['ALL_disable_quant_qdq'], levels['OFF'])
    assert np.array_equal(levels['ALL'][7], levels['OFF'][7])
    # Re-execute both saved controlledfullgraphs, independent of savedmetric JSON.
    for filename, key in [('serialized_ALL_one_Add_restored.onnx', 'patched'),
                          ('actual_ALL_disable_quant_qdq.onnx', 'ALL_disable_quant_qdq')]:
        r = runtime(isolated / filename)
        for i, x in enumerate(levels['inputs']):
            value = r.run(None, {'images': x[None]})[0]
            assert np.array_equal(value, controls[key][i:i+1])
    trace = json.loads((probe / 'common_tensor_trace.json').read_text())
    assert len(trace) == 1060
    for i in [2, 5]:
        rows = [r for r in trace if r['vector'] == i]
        assert len(rows) == 530
        first = next(r for r in rows if r['different_elements'])
        assert first['source_order'] == 100 and first['different_elements'] == 1
        assert first['tensor'] == original_node.output[0]
    result = {'status': 'SERIALIZED_GRAPH_SINGLE_NODE_CAUSAL_CONTROL_AND48_METRICS_INDEPENDENTLY_VERIFIED',
              'job_id': os.environ['SLURM_JOB_ID'],
              'probe_summary_sha256': sha(probe / 'summary.json'), 'isolation_summary_sha256': sha(isolated / 'summary.json'),
              'single_existing_node_changed': True, 'all_other_nodes_and_initializers_unchanged': True,
              'original_typed_common_tensor_rows': 1060, 'metric_conditions': 48,
              'isolated_operator_input_conditions': 8, 'isolated_mismatch_vectors': mismatch_vectors,
              'scalar_mismatch_cases': scalar_cases, 'pass_counts': passed,
              'patched_full_forward_replays': 8, 'no_QDQ_fusion_full_forward_replays': 8,
              'both_controlled_paths_exact_OFF_output': True,
              'vector7_local_difference_but_no_final_embedding_difference': True,
              'new_training_updates': 0, 'all_seeds_gradients_or_FPGA_verified': False,
              'whole_goal_complete': False}
    output = ROOT / 'results/optimizer_independent_verification.json'
    assert not output.exists()
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    (ROOT / 'results/optimizer_independent_metrics.json').write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
