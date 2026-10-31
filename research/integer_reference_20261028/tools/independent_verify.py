"""Independent FP64 exact-integer convolution, not the NumPy im2col code."""
from pathlib import Path
import hashlib, json, os, time, resource
import numpy as np
import torch
import onnx
from onnx import numpy_helper

ROOT = Path('/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028')


def digest(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    assert os.environ.get('SLURM_JOB_ID') and __import__('socket').gethostname() != 'mu01'
    torch.set_num_threads(2)
    torch.backends.mkldnn.enabled = False
    start = time.perf_counter()
    folder = ROOT / 'results/reference'
    summary = json.loads((folder / 'summary.json').read_text())
    protocol = json.loads((ROOT / 'protocol/integer_conv_v1.json').read_text())
    assert summary['protocol_sha256'] == sha(ROOT / 'protocol/integer_conv_v1.json')
    assert summary['candidate_sha256'] == sha(folder / 'integer_accumulator_candidate.onnx')
    for row in protocol['inputs']:
        assert sha(row['remote_source']) == row['sha256']
    layers = json.loads((folder / 'layer_contracts.json').read_text())
    traces = json.loads((folder / 'layer_trace.json').read_text())
    inputs = np.load(folder / 'trace_inputs.npz')
    params = np.load(folder / 'layer_parameters.npz')
    assert len(layers) == 52 and len(traces) == len(inputs.files) == 416
    old_graph = onnx.load(protocol['inputs'][1]['remote_source'])
    old_arrays = {v.name: numpy_helper.to_array(v) for v in old_graph.graph.initializer}
    old_producers = {v: n for n in old_graph.graph.node for v in n.output}
    weight_elements = 0
    for layer in layers:
        old_conv = next(n for n in old_graph.graph.node if n.name == layer['conv_name'])
        dequant = old_producers[old_conv.input[1]]
        original = old_arrays[dequant.input[0]]
        candidate = params[f'l{layer["index"]:02d}_weight']
        assert original.dtype == np.int8 and candidate.dtype == np.uint8
        assert np.array_equal(candidate.astype(np.int16) - 128, original.astype(np.int16))
        weight_elements += original.size
    assert weight_elements == 912008
    independent_rows = []
    for row in traces:
        layer = layers[row['layer']]
        prefix = f'l{row["layer"]:02d}_'
        qx = inputs[row['input_key']]
        weight = params[prefix + 'weight']
        zero = int(params[prefix + 'input_quant_zero'][0])
        assert digest(qx) == row['input_sha256']
        # All dot-product partial sums have magnitude <=INT32 bound <2**53.
        # Integer inputs/products/sums are therefore exactly representable inFP64.
        x = torch.from_numpy(qx.astype(np.float64)) - zero
        w = torch.from_numpy(weight.astype(np.float64)) - 128
        t, l, b, r = layer['pads']
        x = torch.nn.functional.pad(x, (l, r, t, b), value=0.)
        acc = torch.nn.functional.conv2d(x, w, bias=None, stride=layer['strides'], padding=0,
                                         dilation=layer['dilations'], groups=layer['group'])
        assert torch.equal(acc, torch.round(acc))
        values = acc.numpy().astype(np.int64)
        assert digest(values) == row['accumulator_INT64_sha256']
        # Compare against the complete ONNX-model branch, including any upstream drift.
        assert row['ORT_accumulator_exact_reference'] is (row['ORT_accumulator_INT64_sha256'] == digest(values))
        cg, kh, kw = weight.shape[1:]
        bound = cg * kh * kw * max(abs(int(qx.min()) - zero), abs(int(qx.max()) - zero)) * max(
            abs(int(weight.min()) - 128), abs(int(weight.max()) - 128))
        assert bound == row['INT32_worst_absolute_sum_bound'] <= np.iinfo(np.int32).max
        raw = acc * torch.from_numpy(params[prefix + 'input_quant_scale'].astype(np.float64)).reshape(())
        raw = raw * torch.from_numpy(params[prefix + 'weight_quant_scale'].astype(np.float64)).reshape(1, -1, 1, 1)
        raw = raw + torch.from_numpy(params[prefix + 'bias'].astype(np.float64)).reshape(1, -1, 1, 1)
        raw = raw.float()
        assert digest(raw.numpy()) == row['raw_FP32_sha256']
        scale = torch.from_numpy(params[prefix + 'output_quant_scale']).reshape(())
        z = int(params[prefix + 'output_quant_zero'][0])
        q = torch.clamp(torch.round(raw / scale) + z, 0, 255).to(torch.uint8).numpy()
        assert digest(q) == row['output_U8_sha256']
        independent_rows.append({'vector': row['vector'], 'layer': row['layer'], 'accumulator_elements': values.size,
                                 'independent_FP64_integer_exact': True,
                                 'ORT_full_branch_accumulator_exact': row['ORT_accumulator_exact_reference']})
    vectors = np.load(folder / 'whole_model_vectors.npz')
    old_vectors = np.load(protocol['inputs'][2]['remote_source'])
    assert np.array_equal(vectors['inputs'], old_vectors['inputs'])
    conditions = []
    for i in range(8):
        a = vectors['reference'][i].astype(np.float64)
        for condition in ['ORT_disabled', 'ORT_default']:
            b = vectors[condition][i].astype(np.float64)
            # Max difference against originalFP32 output tensors, then cast up for cosine.
            error = float(np.abs(vectors['reference'][i] - vectors[condition][i]).max())
            cosine = float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
            passed = error <= protocol['gates']['maximum_absolute_embedding_difference'] and cosine >= protocol['gates']['minimum_cosine']
            original = summary['candidate_vector_results'][i]['disabled_optimisation' if condition == 'ORT_disabled' else 'default_optimisation']
            assert error == original['maximum_absolute_error'] and abs(cosine - original['cosine']) < 1e-12
            assert passed == original['original_embedding_tolerance_passed']
            conditions.append({'vector': i, 'condition': condition, 'error': error, 'cosine': cosine, 'passed': passed})
    old = json.loads((folder / 'original_failure_reproduction.json').read_text())
    assert [r['vector'] for r in old if not r['original_embedding_tolerance_passed']] == [3]
    graph = onnx.load(folder / 'integer_accumulator_candidate.onnx')
    assert sum(n.op_type == 'ConvInteger' for n in graph.graph.node) == 52
    assert sum(n.op_type == 'Conv' for n in graph.graph.node) == 0
    result = {'status': 'ALL416_INTEGER_ACCUMULATIONS_RECONSTRUCTION_AND16_METRIC_CONDITIONS_INDEPENDENTLY_VERIFIED',
              'job_id': os.environ['SLURM_JOB_ID'], 'protocol_sha256': sha(ROOT / 'protocol/integer_conv_v1.json'),
              'source_summary_sha256': sha(folder / 'summary.json'), 'candidate_sha256': sha(folder / 'integer_accumulator_candidate.onnx'),
              'independent_integer_layer_cases': len(independent_rows),
              'accumulator_elements_recomputed': sum(r['accumulator_elements'] for r in independent_rows),
              'ORT_full_branch_exact_integer_cases': sum(r['ORT_full_branch_accumulator_exact'] for r in independent_rows),
              'equivalent_INT8_weight_elements': weight_elements,
              'candidate_metric_conditions': conditions, 'original_failure_index3_retained': True,
              'new_training_updates': 0, 'new_gradient_or_all_seeds_verified': False,
              'old_QDQ_gate_fixed': False, 'identity_accuracy_or_FPGA_execution_verified': False,
              'verification_process_peak_RSS_KiB': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'elapsed_s': time.perf_counter() - start, 'whole_goal_complete': False}
    path = ROOT / 'results/independent_verification.json'
    assert not path.exists()
    path.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
