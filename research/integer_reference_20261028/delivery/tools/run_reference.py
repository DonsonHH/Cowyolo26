"""Preserve the old failure; test an explicit integer-accumulation candidate."""
from pathlib import Path
import copy, json, os, sys, time, types
import numpy as np
import torch
import onnx
import onnxruntime as ort
from onnx import helper, numpy_helper
from integer_math import convolution, controls, digest, quantise_u8, reconstruct

PROJECT = Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT = PROJECT / 'integer_reference_20261028'
sys.path.insert(0, str(PROJECT / 'qat_study/tools'))
from qat_components import (make_encoder, fold_batchnorm, insert_quantisers,
                            QuantisedConvReference, quant_mode, sha, save, ort_session)


def restore(unpacked, packed, protocol):
    producers = {v: n for n in unpacked.graph.node for v in n.output}
    arrays = {v.name: numpy_helper.to_array(v) for v in unpacked.graph.initializer}
    def constant(name):
        while name not in arrays:
            node = producers[name]
            assert node.op_type == 'Identity'
            name = node.input[0]
        return arrays[name]
    original_protocol = json.loads(Path(protocol['inputs'][3]['remote_source']).read_text())
    model_source = original_protocol['source_models'][0]
    assert sha(model_source['path']) == model_source['sha256']
    model, _ = fold_batchnorm(make_encoder(model_source['path']))
    model, _ = insert_quantisers(model)
    nodes = {n.name: n for n in unpacked.graph.node}
    packed_nodes = {v: n for n in packed.graph.node for v in n.output}
    packed_arrays = {v.name: numpy_helper.to_array(v) for v in packed.graph.initializer}
    layers = []
    for name, module in model.named_modules():
        if not isinstance(module, QuantisedConvReference):
            continue
        weight_name = 'encoder.' + name + '.conv.weight'
        wq = next(n for n in unpacked.graph.node if n.op_type == 'QuantizeLinear' and n.input[0] == weight_name)
        prefix = wq.name.split('/weight_quant/')[0]
        wdq = next(n for n in unpacked.graph.node if n.op_type == 'DequantizeLinear' and n.input[0] == wq.output[0])
        conv = next(n for n in unpacked.graph.node if n.op_type == 'Conv' and n.input[1] == wdq.output[0])
        module.conv.weight.data.copy_(torch.from_numpy(constant(weight_name).copy()))
        module.conv.bias.data.copy_(torch.from_numpy(constant(conv.input[2]).copy()))
        params = {}
        for field in ['input_quant', 'weight_quant', 'output_quant']:
            fq = getattr(module, field)
            q = nodes[prefix + '/' + field + '/QuantizeLinear']
            scale = np.asarray(constant(q.input[1])).copy().reshape(-1)
            zero = np.asarray(constant(q.input[2])).astype(np.int32).reshape(-1)
            fq.scale.resize_(scale.shape).copy_(torch.from_numpy(scale))
            fq.zero_point.resize_(zero.shape).copy_(torch.from_numpy(zero))
            params[field + '_scale'] = scale
            params[field + '_zero'] = zero
        pc = next(n for n in packed.graph.node if n.name == conv.name)
        w = packed_arrays[packed_nodes[pc.input[1]].input[0]]
        assert w.dtype == np.int8
        assert np.all(params['weight_quant_zero'] == 0)
        params['weight'] = (w.astype(np.int16) + 128).astype(np.uint8)
        params['bias'] = constant(conv.input[2]).copy()
        attrs = {a.name: helper.get_attribute_value(a) for a in conv.attribute}
        assert attrs.get('auto_pad', b'NOTSET') == b'NOTSET'
        layers.append({'index': len(layers), 'module': name, 'conv_name': conv.name,
                       'strides': list(attrs.get('strides', [1, 1])),
                       'pads': list(attrs.get('pads', [0, 0, 0, 0])),
                       'dilations': list(attrs.get('dilations', [1, 1])),
                       'group': int(attrs.get('group', 1)), 'params': params})
    assert len(layers) == 52
    quant_mode(model, fake=True, observe=False)
    return model.eval(), layers


def make_candidate(packed, layers):
    graph = copy.deepcopy(packed)
    producers = {v: n for n in graph.graph.node for v in n.output}
    by_conv = {l['conv_name']: l for l in layers}
    new_nodes = []
    for node in graph.graph.node:
        if node.op_type != 'Conv':
            new_nodes.append(node)
            continue
        layer = by_conv[node.name]
        p = layer['params']
        prefix = f'intref_{layer["index"]:02d}'
        def init(suffix, value):
            name = prefix + '_' + suffix
            graph.graph.initializer.append(numpy_helper.from_array(np.asarray(value), name))
            return name
        x_dequant = producers[node.input[0]]
        assert x_dequant.op_type == 'DequantizeLinear'
        weight = init('weightU8', p['weight'])
        wz = init('weightZero', np.array(128, np.uint8))
        xs = init('inputScale64', p['input_quant_scale'].astype(np.float64).reshape(()))
        ws = init('weightScale64', p['weight_quant_scale'].astype(np.float64).reshape(1, -1, 1, 1))
        bias = init('bias64', p['bias'].astype(np.float64).reshape(1, -1, 1, 1))
        acc = prefix + '_acc32'
        layer['accumulator_output'] = acc
        conv = helper.make_node('ConvInteger', [x_dequant.input[0], weight, x_dequant.input[2], wz], [acc],
                                name=prefix + '_ConvInteger')
        conv.attribute.extend(copy.deepcopy(node.attribute))
        new_nodes.extend([conv,
            helper.make_node('Cast', [acc], [prefix + '_acc64'], to=onnx.TensorProto.DOUBLE),
            helper.make_node('Mul', [prefix + '_acc64', xs], [prefix + '_scaledX']),
            helper.make_node('Mul', [prefix + '_scaledX', ws], [prefix + '_scaledW']),
            helper.make_node('Add', [prefix + '_scaledW', bias], [prefix + '_biased']),
            helper.make_node('Cast', [prefix + '_biased'], list(node.output), to=onnx.TensorProto.FLOAT)])
    del graph.graph.node[:]
    graph.graph.node.extend(new_nodes)
    needed = {v.name for v in graph.graph.output}
    retained = []
    for node in reversed(graph.graph.node):
        if needed.intersection(node.output):
            retained.append(node)
            needed.update(node.input)
    del graph.graph.node[:]
    graph.graph.node.extend(reversed(retained))
    initialisers = [v for v in graph.graph.initializer if v.name in needed]
    del graph.graph.initializer[:]
    graph.graph.initializer.extend(initialisers)
    # Old intermediate value_info was absent in the export; avoid stale annotations.
    del graph.graph.value_info[:]
    onnx.checker.check_model(graph, full_check=True)
    return graph


def metrics(a, b):
    error = float(np.max(np.abs(a - b)))
    cosine = float(np.sum(a.astype(np.float64) * b.astype(np.float64)) /
                   (np.linalg.norm(a.astype(np.float64)) * np.linalg.norm(b.astype(np.float64))))
    return {'maximum_absolute_error': error, 'cosine': cosine,
            'original_embedding_tolerance_passed': error <= .001 and cosine >= .9999}


def main():
    assert os.environ.get('SLURM_JOB_ID') and __import__('socket').gethostname() != 'mu01'
    torch.set_num_threads(2)
    torch.backends.mkldnn.enabled = True
    protocol_path = ROOT / 'protocol/integer_conv_v1.json'
    protocol = json.loads(protocol_path.read_text())
    for row in protocol['inputs']:
        path = Path(row['remote_source'])
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
    out = ROOT / 'results/reference'
    out.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    save(out / 'scalar_controls.json', controls())
    old_root = PROJECT / 'qat_study/results/smoke'
    unpacked = onnx.load(old_root / 'initial_qat_unpacked.onnx')
    packed = onnx.load(old_root / 'initial_qat_packed.onnx')
    saved = np.load(old_root / 'export_parity_vectors.npz')
    assert saved['inputs'].shape == (8, 3, 224, 224)
    model, layers = restore(unpacked, packed, protocol)
    old_session = ort_session(old_root / 'initial_qat_packed.onnx')
    old_rows = []
    with torch.no_grad():
        for i, x in enumerate(saved['inputs']):
            x = x[None]
            a = torch.nn.functional.normalize(model(torch.from_numpy(x)), dim=1).numpy()
            b = old_session.run(None, {'images': x})[0]
            row = {'vector': i, **metrics(a, b),
                   'ORT_exact_saved_output': np.array_equal(b, saved['packed'][i:i+1]),
                   'Torch_exact_saved_output': np.array_equal(a, saved['torch'][i:i+1])}
            old_rows.append(row)
    save(out / 'original_failure_reproduction.json', old_rows)
    assert all(r['ORT_exact_saved_output'] and r['Torch_exact_saved_output'] for r in old_rows)
    assert [r['vector'] for r in old_rows if not r['original_embedding_tolerance_passed']] == [3]
    print(json.dumps({'event': 'ORIGINAL_FAILURE_REPRODUCED', 'passed': 7, 'failed_vectors': [3]}), flush=True)
    candidate = make_candidate(packed, layers)
    candidate_path = out / 'integer_accumulator_candidate.onnx'
    onnx.save(candidate, candidate_path)
    parameter_arrays = {}
    contracts = []
    for layer in layers:
        for key, value in layer['params'].items():
            parameter_arrays[f'l{layer["index"]:02d}_{key}'] = value
        contracts.append({k: v for k, v in layer.items() if k != 'params'})
    np.savez_compressed(out / 'layer_parameters.npz', **parameter_arrays)
    save(out / 'layer_contracts.json', contracts)
    trace, trace_inputs = [], {}
    modules = dict(model.named_modules())
    vector_index = [None]
    def replacement(layer):
        def forward(self, tensor):
            assert not torch.is_grad_enabled(), 'Numerical-only reference has no implemented training gradient'
            p = layer['params']
            qx = quantise_u8(tensor.detach().numpy(), p['input_quant_scale'], p['input_quant_zero'])
            acc, bound = convolution(qx, p['weight'], int(p['input_quant_zero'][0]), 128,
                                     layer['strides'], layer['pads'], layer['dilations'], layer['group'])
            raw = reconstruct(acc, p['input_quant_scale'], p['weight_quant_scale'], p['bias'])
            qy = quantise_u8(raw, p['output_quant_scale'], p['output_quant_zero'])
            value = (qy.astype(np.float32) - np.float32(p['output_quant_zero'][0])) * np.float32(p['output_quant_scale'][0])
            key = f'v{vector_index[0]}_l{layer["index"]:02d}'
            trace_inputs[key] = qx
            trace.append({'vector': vector_index[0], 'layer': layer['index'], 'module': layer['module'],
                          'input_key': key, 'input_shape': list(qx.shape), 'accumulator_shape': list(acc.shape),
                          'input_sha256': digest(qx), 'accumulator_INT64_sha256': digest(acc),
                          'raw_FP32_sha256': digest(raw), 'output_U8_sha256': digest(qy),
                          'INT32_worst_absolute_sum_bound': bound,
                          'maximum_absolute_accumulator': int(np.max(np.abs(acc)))})
            return torch.from_numpy(value)
        return forward
    for layer in layers:
        module = modules[layer['module']]
        module.forward = types.MethodType(replacement(layer), module)
    augmented = copy.deepcopy(candidate)
    augmented.graph.output.extend([helper.make_tensor_value_info(l['accumulator_output'], onnx.TensorProto.INT32, None)
                                   for l in layers])
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
    runtime = ort.InferenceSession(augmented.SerializeToString(), sess_options=options, providers=['CPUExecutionProvider'])
    normal = ort_session(candidate_path)
    optimised = ort_session(candidate_path, True)
    results, reference_outputs, runtime_outputs, optimised_outputs = [], [], [], []
    for i, x in enumerate(saved['inputs']):
        x = x[None]
        vector_index[0] = i
        with torch.no_grad():
            a = torch.nn.functional.normalize(model(torch.from_numpy(x)), dim=1).numpy()
        values = runtime.run(None, {'images': x})
        b = values[0]
        c = normal.run(None, {'images': x})[0]
        d = optimised.run(None, {'images': x})[0]
        rows = [r for r in trace if r['vector'] == i]
        assert len(rows) == len(values) - 1 == 52
        for r, accumulator in zip(rows, values[1:]):
            assert accumulator.dtype == np.int32
            r['ORT_accumulator_INT64_sha256'] = digest(accumulator.astype(np.int64))
            r['ORT_accumulator_exact_reference'] = r['ORT_accumulator_INT64_sha256'] == r['accumulator_INT64_sha256']
        results.append({'vector': i, 'disabled_optimisation': metrics(a, b), 'default_optimisation': metrics(a, d),
                        'accumulator_exact_layers': sum(r['ORT_accumulator_exact_reference'] for r in rows),
                        'normal_and_augmented_output_equal': np.array_equal(b, c),
                        'candidate_vs_old_QDQ_output_error': float(np.max(np.abs(b - saved['packed'][i:i+1]))),
                        'default_vs_disabled_maximum_error': float(np.max(np.abs(b - d)))})
        reference_outputs.append(a)
        runtime_outputs.append(b)
        optimised_outputs.append(d)
        print(json.dumps({'event': 'INTEGER_REFERENCE_VECTOR', **results[-1]}), flush=True)
    np.savez_compressed(out / 'trace_inputs.npz', **trace_inputs)
    np.savez_compressed(out / 'whole_model_vectors.npz', inputs=saved['inputs'], reference=np.concatenate(reference_outputs),
                        ORT_disabled=np.concatenate(runtime_outputs), ORT_default=np.concatenate(optimised_outputs))
    save(out / 'layer_trace.json', trace)
    save(out / 'vector_results.json', results)
    summary = {'status': 'EXPLICIT_INTEGER_CANDIDATE_NUMERICAL_PROBE_COMPLETE', 'job_id': os.environ['SLURM_JOB_ID'],
               'protocol_sha256': sha(protocol_path), 'candidate_sha256': sha(candidate_path),
               'versions': {'torch': torch.__version__, 'numpy': np.__version__, 'onnx': onnx.__version__, 'ORT': ort.__version__},
               'old_failure_reproduced_exactly': True, 'old_passed_vectors': 7, 'old_failed_vectors': [3],
               'candidate_passed_vectors': sum(r['disabled_optimisation']['original_embedding_tolerance_passed'] for r in results),
               'candidate_default_passed_vectors': sum(r['default_optimisation']['original_embedding_tolerance_passed'] for r in results),
               'integer_accumulator_exact_cases': sum(r['ORT_accumulator_exact_reference'] for r in trace),
               'total_layer_cases': len(trace), 'candidate_vector_results': results,
               'candidate_is_changed_numerical_contract': True, 'original_QDQ_gate_fixed': False,
               'new_training_updates': 0, 'new_training_gradient_verified': False,
               'new_image_reads': 0, 'identity_accuracy_evaluated': False, 'FPGA_executed': False,
               'elapsed_s': time.perf_counter() - start, 'whole_goal_complete': False}
    save(out / 'summary.json', summary)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
