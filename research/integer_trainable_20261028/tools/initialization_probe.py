"""Check CPU/GPU Conv-BN folding against both frozen numerical candidates."""
from pathlib import Path
import json, os, sys
import numpy as np
import torch
import onnx
from onnx import numpy_helper
PROJECT = Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT = PROJECT / 'integer_trainable_20261028'
sys.path.insert(0, str(PROJECT / 'qat_study/tools'))
from qat_components import make_encoder, fold_batchnorm, sha, save


def main():
    assert os.environ.get('SLURM_JOB_ID') and torch.cuda.is_available()
    torch.set_num_threads(2)
    p = json.loads((ROOT / 'protocol/trainable_integer_smoke_v1.json').read_text())
    source = p['source_models'][0]
    assert sha(source['path']) == source['sha256']
    cpu, _ = fold_batchnorm(make_encoder(source['path']).cpu())
    gpu, _ = fold_batchnorm(make_encoder(source['path']).cuda())
    graph = onnx.load(PROJECT / 'qat_study/results/smoke/initial_qat_unpacked.onnx')
    arrays = {v.name: numpy_helper.to_array(v) for v in graph.graph.initializer}
    old = np.load(PROJECT / 'integer_reference_20261028/results/reference/layer_parameters.npz')
    contracts = json.loads((PROJECT / 'integer_reference_20261028/results/reference/layer_contracts.json').read_text())
    state = torch.load(ROOT / 'results/smoke_v2/seed26_initial/state.pt', map_location='cpu', weights_only=True)
    layers = []
    for layer in contracts:
        name, index = layer['module'], layer['index']
        cw = cpu.get_submodule(name).weight.detach().numpy()
        gw = gpu.get_submodule(name).weight.detach().cpu().numpy()
        cb = cpu.get_submodule(name).bias.detach().numpy()
        gb = gpu.get_submodule(name).bias.detach().cpu().numpy()
        sw = state[name + '.conv.weight'].numpy()
        sb = state[name + '.conv.bias'].numpy()
        ow = arrays['encoder.' + name + '.conv.weight']
        ob = old[f'l{index:02d}_bias']
        # These are all pre-update weights. Only metadata/weight arithmetic here.
        assert np.array_equal(cw, sw) and np.array_equal(cb, sb)
        newscale = state[name + '.sw'].numpy()
        newcode = (np.clip(np.rint(sw / newscale.reshape(-1, 1, 1, 1)), -128, 127).astype(np.int16) + 128).astype(np.uint8)
        qp = {}
        for new, oldname in [('sx', 'input_quant_scale'), ('zx', 'input_quant_zero'),
                             ('sw', 'weight_quant_scale'), ('zw', 'weight_quant_zero'),
                             ('sy', 'output_quant_scale'), ('zy', 'output_quant_zero')]:
            aa = state[name + '.' + new].numpy().reshape(-1)
            bb = old[f'l{index:02d}_{oldname}'].reshape(-1)
            assert aa.shape == bb.shape
            qp[new] = {'different_elements': int(np.count_nonzero(aa != bb)),
                       'maximum_absolute_difference': float(np.max(np.abs(aa.astype(float) - bb.astype(float))))}
        layers.append({'module': name, 'new_state_exact_CPU_fold_weights_bias': True,
                       'old_graph_exact_GPU_fold_weights': np.array_equal(gw, ow),
                       'old_graph_exact_GPU_fold_bias': np.array_equal(gb, ob),
                       'CPU_GPU_weight_different_elements': int(np.count_nonzero(cw != gw)),
                       'CPU_GPU_weight_maximum_difference': float(np.max(np.abs(cw - gw))),
                       'CPU_GPU_bias_different_elements': int(np.count_nonzero(cb != gb)),
                       'CPU_GPU_bias_maximum_difference': float(np.max(np.abs(cb - gb))),
                       'new_vs_old_weight_code_different_elements': int(np.count_nonzero(newcode != old[f'l{index:02d}_weight'])),
                       'qparam_differences': qp})
    oldvalues = np.load(PROJECT / 'integer_reference_20261028/results/reference/whole_model_vectors.npz')
    newvalues = np.load(ROOT / 'results/smoke_v2/seed26_initial/vectors.npz')
    summary = {'status': 'CPU_GPU_FOLD_AND_QUANTIZER_INITIALIZATION_DIFFERENCES_MEASURED', 'job_id': os.environ['SLURM_JOB_ID'],
               'seed': 26, 'source_checkpoint_sha256': source['sha256'], 'layers': layers,
               'new_all52_weights_bias_exact_CPU_fold': True,
               'old_GPU_fold_weight_exact_layers': sum(r['old_graph_exact_GPU_fold_weights'] for r in layers),
               'old_GPU_fold_bias_exact_layers': sum(r['old_graph_exact_GPU_fold_bias'] for r in layers),
               'CPU_GPU_weight_different_elements': sum(r['CPU_GPU_weight_different_elements'] for r in layers),
               'maximum_CPU_GPU_weight_difference': max(r['CPU_GPU_weight_maximum_difference'] for r in layers),
               'maximum_CPU_GPU_bias_difference': max(r['CPU_GPU_bias_maximum_difference'] for r in layers),
               'changed_quantized_weight_elements': sum(r['new_vs_old_weight_code_different_elements'] for r in layers),
               'layers_with_quantizer_parameter_differences': sum(any(v['different_elements'] for v in r['qparam_differences'].values()) for r in layers),
               'seed26_new_old_feature_maximum_difference': float(np.max(np.abs(newvalues['CPU'] - oldvalues['reference']))),
               'source_checkpoint_and_input_tensors_unchanged': np.array_equal(newvalues['inputs'], oldvalues['inputs']),
               'new_training_updates_or_images_read': 0, 'whole_goal_complete': False}
    save(ROOT / 'results/initialization_probe.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k != 'layers'}), flush=True)


if __name__ == '__main__':
    main()
