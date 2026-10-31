"""Recompute every Conv using independent INT64 im2col and replay ORT."""
from pathlib import Path
import copy, hashlib, json, os, sys, types
import numpy as np
import torch
import torch.nn.functional as F
import onnx
from onnx import helper, numpy_helper
PROJECT = Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT = PROJECT / 'integer_trainable_20261028'
sys.path.insert(0, str(PROJECT / 'qat_study/tools'))
sys.path.insert(0, str(PROJECT / 'integer_reference_20261028/tools'))
from qat_components import make_encoder, fold_batchnorm, insert_quantisers, sha, save
from integer_trainable import convert, TrainableIntegerConv, gradient_controls, parameters_digest
from integer_math import quantise_u8, convolution, reconstruct, digest
from smoke import runtime, metric


def restored(source, state):
    model, _ = fold_batchnorm(make_encoder(source['path']))
    model, _ = insert_quantisers(model)
    model, _ = convert(model)
    for name, buffer in model.named_buffers():
        buffer.resize_(state[name].shape)
    model.load_state_dict(state)
    return model.eval()


def main():
    assert os.environ.get('SLURM_JOB_ID') and __import__('socket').gethostname() != 'mu01'
    torch.set_num_threads(2)
    torch.backends.mkldnn.enabled = True
    p = json.loads((ROOT / 'protocol/trainable_integer_smoke_v1.json').read_text())
    folder = ROOT / 'results/smoke_v2'
    summary = json.loads((folder / 'summary.json').read_text())
    assert summary['protocol_sha256'] == sha(ROOT / 'protocol/trainable_integer_smoke_v1.json')
    assert summary['source_input_vectors_unchanged'] is True
    assert summary['actual_discarded_smoke_updates'] in [0, 6]
    assert summary['formal_QAT_updates'] == 0 and summary['validation_or_holdout_image_reads'] == 0
    train_manifest = PROJECT / 'identity_training/results/input_audit/manifest.json'
    assert sha(train_manifest) == p['manifest_sha256']
    train = [r for r in json.loads(train_manifest.read_text()) if r['split'] == 'train']
    training = {r['relative_path']: r for r in train}
    access = json.loads((folder / 'training_image_access_log.json').read_text())
    assert len({r['relative_path'] for r in access}) == len(access)
    for row in access:
        assert row['split'] == training[row['relative_path']]['split'] == 'train'
        assert row['sha256'] == training[row['relative_path']]['sha256'] == sha(PROJECT / 'identity_training' / row['relative_path'])
    diagnosis = json.loads((ROOT / 'results/backward_probe/summary.json').read_text())
    assert len(diagnosis['conditions']) == 4 and diagnosis['optimizer_steps'] == 0
    for row in diagnosis['conditions']:
        assert row['missing_gradient_tensors'] == row['frozen_parameter_tensors']
        assert len(row['missing_gradient_tensors']) == 34 and row['nonfinite_gradient_tensors'] == []
    # Independently recheck declaredSTE on CPU; GPUcontrols are from the actual GPU smoke.
    cpu_gradient_controls = gradient_controls('cpu')
    old_vectors = np.load(PROJECT / 'qat_study/results/smoke/export_parity_vectors.npz')
    cases, metric_rows = [], []
    integer_cases = accumulator_elements = 0
    for record, source in zip(summary['seeds'], p['source_models']):
        assert record['seed'] == source['seed']
        assert sha(source['path']) == source['sha256']
        states = {}
        for phase in ['initial', 'post2updates']:
            if phase == 'post2updates' and record['post_update'] is None:
                continue
            directory = folder / f'seed{source["seed"]}_{phase}'
            primary = json.loads((directory / 'summary.json').read_text())
            assert primary['packed_sha256'] == sha(directory / 'packed.onnx')
            assert primary['state_sha256'] == sha(directory / 'state.pt')
            state = torch.load(directory / 'state.pt', map_location='cpu', weights_only=True)
            states[phase] = state
            model = restored(source, state)
            assert parameters_digest(model) == record['frozen_qparams_sha256']
            values = np.load(directory / 'vectors.npz')
            assert np.array_equal(values['inputs'], old_vectors['inputs'])
            if phase == 'initial':
                prior = np.load(ROOT / f'results/smoke/seed{source["seed"]}_initial/vectors.npz')
                assert np.array_equal(values['CPU'], prior['CPU']) and np.array_equal(values['inputs'], prior['inputs'])
            graph = onnx.load(directory / 'packed.onnx')
            convs = [n for n in graph.graph.node if n.op_type == 'ConvInteger']
            assert len(convs) == 52 and not any(n.op_type == 'Conv' for n in graph.graph.node)
            arrays = {v.name: numpy_helper.to_array(v) for v in graph.graph.initializer}
            trace = []
            for index, (name, module) in enumerate([(n, m) for n, m in model.named_modules() if isinstance(m, TrainableIntegerConv)]):
                def make_forward(layer_index):
                    def forward(self, tensor):
                        qx = quantise_u8(tensor.detach().numpy(), self.sx.numpy(), self.zx.numpy())
                        sw = self.sw.numpy()
                        w = self.conv.weight.detach().numpy()
                        code = (np.clip(np.rint(w / sw.reshape(-1, 1, 1, 1)), -128, 127).astype(np.int16) + 128).astype(np.uint8)
                        assert np.array_equal(code, arrays[convs[layer_index].input[1]])
                        py, px = self.conv.padding
                        acc, bound = convolution(qx, code, int(self.zx), 128, self.conv.stride,
                                                 [py, px, py, px], self.conv.dilation, self.conv.groups)
                        raw = reconstruct(acc, self.sx.numpy(), sw, self.conv.bias.detach().numpy())
                        qy = quantise_u8(raw, self.sy.numpy(), self.zy.numpy())
                        trace.append({'layer': layer_index, 'accumulator_sha256': digest(acc),
                                      'elements': acc.size, 'INT32_bound': bound})
                        return torch.from_numpy((qy.astype(np.float32) - np.float32(self.zy)) * np.float32(self.sy))
                    return forward
                module.forward = types.MethodType(make_forward(index), module)
            augmented = copy.deepcopy(graph)
            augmented.graph.output.extend([helper.make_tensor_value_info(n.output[0], onnx.TensorProto.INT32, None) for n in convs])
            r = runtime(augmented.SerializeToString(), 'OFF')
            selected = runtime(directory / 'packed.onnx', 'ALL_disable_quant_qdq')
            exact_layers = 0
            for i, x in enumerate(values['inputs']):
                trace.clear()
                with torch.no_grad():
                    reference = F.normalize(model(torch.from_numpy(x[None])), dim=1).numpy()
                outputs = r.run(None, {'images': x[None]})
                assert np.array_equal(outputs[0], values['OFF'][i:i+1])
                assert len(trace) == 52
                for row, acc in zip(trace, outputs[1:]):
                    assert acc.dtype == np.int32
                    assert digest(acc.astype(np.int64)) == row['accumulator_sha256']
                    integer_cases += 1
                    accumulator_elements += row['elements']
                    exact_layers += 1
                same_reference = metric(reference, values['CPU'][i:i+1])
                assert same_reference['pass']
                assert np.array_equal(selected.run(None, {'images': x[None]})[0], values['ALL_disable_quant_qdq'][i:i+1])
                row = {'seed': source['seed'], 'phase': phase, 'vector': i,
                       'independent_INT64_reference_vs_CPU': same_reference,
                       'integer_accumulator_layers_exact': 52}
                for condition in p['runtime_conditions']:
                    actual = metric(values['CPU'][i:i+1], values[condition][i:i+1])
                    primary_metric = primary['rows'][i]['runtime'][condition]
                    assert actual['maximum_absolute_error'] == primary_metric['maximum_absolute_error']
                    assert abs(actual['cosine'] - primary_metric['cosine']) < 1e-12 and actual['pass'] == primary_metric['pass']
                    row[condition] = actual
                assert metric(values['CPU'][i:i+1], values['GPU'][i:i+1]) == primary['rows'][i]['GPU_CPU']
                assert float(np.max(np.abs(values['unpacked'][i] - values['OFF'][i]))) == primary['rows'][i]['packing_max_error']
                metric_rows.append(row)
            cases.append({'seed': source['seed'], 'phase': phase, 'exact_integer_accumulator_layers': exact_layers,
                          'required_all_vectors_pass': primary['required_all_vectors_pass'], 'runtime_passes': primary['runtime_passes']})
        if 'post2updates' in states:
            model = restored(source, states['initial'])
            parameter_names = {n for n, _ in model.named_parameters()}
            buffer_names = {n for n, _ in model.named_buffers()}
            changed = [n for n in parameter_names if not torch.equal(states['initial'][n], states['post2updates'][n])]
            assert len(changed) == record['changed_parameter_tensors'] > 0
            assert all(torch.equal(states['initial'][n], states['post2updates'][n]) for n in buffer_names)
            assert record['discarded_smoke_updates'] == 2
            assert len(record['updates']) == 2 and all(r['finite_gradient_tensors'] == 104 for r in record['updates'])
    result = {'status': 'TRAIN_INPUTS_SIX_MODEL_EXPORTS_AND_INTEGER_FORWARD_INDEPENDENTLY_VERIFIED',
              'job_id': os.environ['SLURM_JOB_ID'], 'protocol_sha256': sha(ROOT / 'protocol/trainable_integer_smoke_v1.json'),
              'source_summary_sha256': sha(folder / 'summary.json'), 'model_conditions': cases,
              'integer_accumulator_layer_cases': integer_cases, 'accumulator_elements_recomputed': accumulator_elements,
              'feature_vector_conditions': len(metric_rows), 'runtime_metric_conditions': len(metric_rows) * 3,
              'training_image_access_count': len(access), 'training_image_roles_and_hashes_verified': True,
              'initial_outputs_unchanged_by_trainability_fix': True, 'frozen_bias_failure_verified': True,
              'independent_CPU_STE_controls': cpu_gradient_controls,
              'actual_discarded_smoke_updates': summary['actual_discarded_smoke_updates'],
              'formal_QAT_updates': 0, 'FPGA_execution_verified': False, 'whole_goal_complete': False}
    save(ROOT / 'results/independent_verification.json', result)
    save(ROOT / 'results/independent_feature_conditions.json', metric_rows)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
