"""Single-node causal control on the actual serialized optimized graph."""
from pathlib import Path
from collections import Counter
import copy, hashlib, json, os, time
import numpy as np
import onnx
from onnx import helper, numpy_helper
from optimizer_probe import augment, metric, node_record, session, sha, save

ROOT = Path('/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028')


def replacement(node):
    assert node.op_type == 'QLinearAdd' and node.domain == 'com.microsoft' and len(node.input) == 8
    a, sa, za, b, sb, zb, sy, zy = node.input
    prefix = 'causal_restore_first_residual'
    return [helper.make_node('DequantizeLinear', [a, sa, za], [prefix + '_a']),
            helper.make_node('DequantizeLinear', [b, sb, zb], [prefix + '_b']),
            helper.make_node('Add', [prefix + '_a', prefix + '_b'], [prefix + '_sum']),
            helper.make_node('QuantizeLinear', [prefix + '_sum', sy, zy], list(node.output))]


def isolated(graph, node, metadata, initializers, fused):
    nodes = [copy.deepcopy(node)] if fused else replacement(node)
    assert all(node.input[j] in initializers for j in [1, 2, 4, 5, 6, 7])
    constants = [copy.deepcopy(initializers[v]) for v in dict.fromkeys(node.input) if v in initializers]
    inputs = [copy.deepcopy(metadata[v]) for v in [node.input[0], node.input[3]]]
    output = copy.deepcopy(metadata[node.output[0]])
    sub = helper.make_model(helper.make_graph(nodes, 'Fixed_same_inputs_residual_control', inputs, [output], constants),
                            opset_imports=copy.deepcopy(graph.opset_import), ir_version=graph.ir_version)
    return sub


def main():
    assert os.environ.get('SLURM_JOB_ID') and __import__('socket').gethostname() != 'mu01'
    start = time.perf_counter()
    probe_dir = ROOT / 'results/optimizer_probe'
    protocol_path = ROOT / 'protocol/optimizer_isolation_v1.json'
    protocol = json.loads(protocol_path.read_text())
    assert sha(probe_dir / 'actual_optimized_ALL.onnx') == protocol['serialized_ALL_sha256']
    assert sha(ROOT / 'results/reference/integer_accumulator_candidate.onnx') == protocol['source_candidate_sha256']
    firsts = json.loads((probe_dir / 'first_divergences.json').read_text())
    assert len(firsts) == 2 and [r['vector'] for r in firsts] == [2, 5]
    names = [r['first_common_integer_difference']['optimized_producer']['name'] for r in firsts]
    assert len(set(names)) == 1
    graph = onnx.load(probe_dir / 'actual_optimized_ALL.onnx')
    original = onnx.load(ROOT / 'results/reference/integer_accumulator_candidate.onnx')
    typed = onnx.shape_inference.infer_shapes(original)
    metadata = {v.name: v for v in list(typed.graph.value_info) + list(typed.graph.input) + list(typed.graph.output)}
    node = next(n for n in graph.graph.node if n.name == names[0])
    assert node_record(node) == firsts[0]['first_common_integer_difference']['optimized_producer']
    assert node.op_type == 'QLinearAdd' and node.domain == 'com.microsoft'
    assert protocol['target_node'] == node.name
    out = ROOT / 'results/optimizer_isolation'
    out.mkdir(exist_ok=False)
    arrays = {v.name: numpy_helper.to_array(v) for v in graph.graph.initializer}
    inits = {v.name: v for v in graph.graph.initializer}
    names_to_capture = [node.input[0], node.input[3], node.output[0]]
    raw_probe = session(augment(original, names_to_capture, metadata).SerializeToString(), 'OFF')
    opt_probe = session(augment(graph, names_to_capture, metadata).SerializeToString(), 'OFF')
    raw_names = [v.name for v in raw_probe.get_outputs()]
    opt_names = [v.name for v in opt_probe.get_outputs()]
    fused = isolated(graph, node, metadata, inits, True)
    expanded = isolated(graph, node, metadata, inits, False)
    onnx.save(fused, out / 'isolated_QLinearAdd.onnx')
    onnx.save(expanded, out / 'isolated_DQ_Add_Q.onnx')
    fused_runtime = session(fused.SerializeToString(), 'OFF')
    expanded_runtime = session(expanded.SerializeToString(), 'OFF')
    patched = copy.deepcopy(graph)
    new_nodes = []
    replaced = 0
    for current in patched.graph.node:
        if current.name == node.name:
            new_nodes.extend(replacement(current))
            replaced += 1
        else:
            new_nodes.append(current)
    assert replaced == 1
    del patched.graph.node[:]
    patched.graph.node.extend(new_nodes)
    onnx.save(patched, out / 'serialized_ALL_one_Add_restored.onnx')
    patched_runtime = session(patched.SerializeToString(), 'OFF')
    # Documented sessionflag disables QDQ fusions broadly; this is a separate control.
    import onnxruntime as ort
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    options.add_session_config_entry('session.disable_quant_qdq', '1')
    options.optimized_model_filepath = str(out / 'actual_ALL_disable_quant_qdq.onnx')
    no_fusion = ort.InferenceSession(str(ROOT / 'results/reference/integer_accumulator_candidate.onnx'),
                                    sess_options=options, providers=['CPUExecutionProvider'])
    vectors = np.load(probe_dir / 'level_embeddings.npz')
    records, tensors, outputs = [], {}, {'patched': [], 'ALL_disable_quant_qdq': []}
    sa, za, sb, zb, sy, zy = [np.asarray(arrays[node.input[j]]).reshape(()) for j in [1, 2, 4, 5, 6, 7]]
    for i, x in enumerate(vectors['inputs']):
        x = x[None]
        original_values = dict(zip(raw_names, raw_probe.run(None, {'images': x})))
        optimized_values = dict(zip(opt_names, opt_probe.run(None, {'images': x})))
        assert np.array_equal(original_values['embedding'], vectors['OFF'][i:i+1])
        assert np.array_equal(optimized_values['embedding'], vectors['ALL'][i:i+1])
        a, b = [original_values[n] for n in [node.input[0], node.input[3]]]
        assert np.array_equal(a, optimized_values[node.input[0]])
        assert np.array_equal(b, optimized_values[node.input[3]])
        feed = {node.input[0]: a, node.input[3]: b}
        fq = fused_runtime.run(None, feed)[0]
        uq = expanded_runtime.run(None, feed)[0]
        assert np.array_equal(fq, optimized_values[node.output[0]])
        assert np.array_equal(uq, original_values[node.output[0]])
        da = (a.astype(np.float32) - np.asarray(za, dtype=np.float32)) * np.asarray(sa, dtype=np.float32)
        db = (b.astype(np.float32) - np.asarray(zb, dtype=np.float32)) * np.asarray(sb, dtype=np.float32)
        ratio_unfused = ((da + db) / np.asarray(sy, dtype=np.float32)).astype(np.float32)
        nq = np.clip(np.rint(ratio_unfused) + np.asarray(zy, dtype=np.float32), 0, 255).astype(np.uint8)
        assert np.array_equal(nq, uq)
        ratio_scaled = ((a.astype(np.float32) - np.asarray(za, dtype=np.float32)) * (np.asarray(sa, dtype=np.float32) / np.asarray(sy, dtype=np.float32))
                        + (b.astype(np.float32) - np.asarray(zb, dtype=np.float32)) * (np.asarray(sb, dtype=np.float32) / np.asarray(sy, dtype=np.float32)))
        mismatches = np.argwhere(fq != uq)
        details = []
        for index in mismatches:
            loc = tuple(int(v) for v in index)
            details.append({'index': list(loc), 'A': int(a[loc]), 'B': int(b[loc]),
                            'unfused_U8': int(uq[loc]), 'fused_U8': int(fq[loc]),
                            'unfused_FP32_units': float(ratio_unfused[loc]),
                            'scaled_ratio_FP32_control_units': float(ratio_scaled[loc]),
                            'ideal_FP64_units': float((float(a[loc]) - float(za)) * float(sa) / float(sy)
                                                     + (float(b[loc]) - float(zb)) * float(sb) / float(sy))})
        fixed = patched_runtime.run(None, {'images': x})[0]
        broad = no_fusion.run(None, {'images': x})[0]
        outputs['patched'].append(fixed)
        outputs['ALL_disable_quant_qdq'].append(broad)
        for key, value in [('A', a), ('B', b), ('fused', fq), ('unfused', uq)]:
            tensors[f'v{i}_{key}'] = value
        row = {'vector': i, 'same_source_and_ALL_upstream_integer_inputs': True,
               'isolated_fused_exact_full_ALL_node': True, 'isolated_unfused_exact_full_OFF_node': True,
               'isolated_output_different_elements': len(mismatches), 'differences': details,
               'patched_one_node': metric(vectors['reference'][i:i+1], fixed),
               'patched_exact_OFF_embedding': np.array_equal(fixed, vectors['OFF'][i:i+1]),
               'disable_quant_qdq': metric(vectors['reference'][i:i+1], broad),
               'disable_quant_qdq_exact_OFF_embedding': np.array_equal(broad, vectors['OFF'][i:i+1])}
        records.append(row)
        print(json.dumps({'event': 'SINGLE_ADD_CAUSAL_CONTROL', **row}), flush=True)
    np.savez_compressed(out / 'isolated_node_vectors.npz', **tensors)
    np.savez_compressed(out / 'controlled_embeddings.npz', inputs=vectors['inputs'], reference=vectors['reference'],
                        OFF=vectors['OFF'], ALL=vectors['ALL'], **{k: np.concatenate(v) for k, v in outputs.items()})
    # Existing optimized nodes before/after the targetedQLinearAdd are copied unchanged.
    position = next(i for i, n in enumerate(graph.graph.node) if n.name == node.name)
    assert len(patched.graph.node) == len(graph.graph.node) + 3
    assert [n.SerializeToString() for n in graph.graph.node[:position]] == [n.SerializeToString() for n in patched.graph.node[:position]]
    assert [n.SerializeToString() for n in graph.graph.node[position+1:]] == [n.SerializeToString() for n in patched.graph.node[position+4:]]
    summary = {'status': 'SAME_INPUT_ISOLATED_ADD_AND_SINGLE_NODE_FULL_GRAPH_CONTROLS_COMPLETE',
               'job_id': os.environ['SLURM_JOB_ID'], 'protocol_sha256': sha(protocol_path),
               'source_serialized_ALL_sha256': sha(probe_dir / 'actual_optimized_ALL.onnx'),
               'target_node': node_record(node), 'replaced_nodes': replaced,
               'other_existing_nodes_unchanged': True,
               'isolated_mismatch_vectors': [r['vector'] for r in records if r['isolated_output_different_elements']],
               'patched_passed_vectors': sum(r['patched_one_node']['passed_original_embedding_tolerance'] for r in records),
               'patched_exact_OFF_vectors': sum(r['patched_exact_OFF_embedding'] for r in records),
               'disable_quant_qdq_passed_vectors': sum(r['disable_quant_qdq']['passed_original_embedding_tolerance'] for r in records),
               'disable_quant_qdq_exact_OFF_vectors': sum(r['disable_quant_qdq_exact_OFF_embedding'] for r in records),
               'new_training_updates': 0, 'new_image_reads': 0, 'all_training_seeds_verified': False,
               'FPGA_execution_verified': False, 'elapsed_s': time.perf_counter() - start,
               'whole_goal_complete': False}
    save(out / 'records.json', records)
    save(out / 'summary.json', summary)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
