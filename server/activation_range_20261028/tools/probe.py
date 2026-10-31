from pathlib import Path
import copy, hashlib, json, os, random, sys, time, types
import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F
PROJECT = Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT = PROJECT / 'activation_range_20261028'
sys.path.insert(0, str(PROJECT / 'qat_study/tools'))
sys.path.insert(0, str(PROJECT / 'identity_training/tools'))
sys.path.insert(0, str(PROJECT / 'integer_trainable_20261028/tools'))
from qat_components import make_encoder, fold_batchnorm, insert_quantisers, sha, save
from integer_trainable import convert, TrainableIntegerConv, parameters_digest
from training_primitives import BodyTransform


def restore(source, row):
    model, _ = fold_batchnorm(make_encoder(source['path']))
    if row['quantized']:
        model, _ = insert_quantisers(model)
        model, _ = convert(model)
    state = torch.load(row['remote_path'], map_location='cpu', weights_only=True)
    for name, buffer in model.named_buffers(): buffer.resize_(state[name].shape)
    model.load_state_dict(state)
    return model.eval().requires_grad_(False)


def stats(code, minimum, maximum):
    assert torch.isfinite(code).all()
    return torch.stack([torch.as_tensor(code.numel(), dtype=torch.int64, device=code.device),
                        (code < minimum).sum(), (code > maximum).sum(),
                        (code == minimum).sum(), (code == maximum).sum()])


def weight_digest(model):
    value = hashlib.sha256()
    for name, parameter in model.named_parameters():
        value.update(name.encode())
        value.update(parameter.detach().cpu().numpy().tobytes())
    return value.hexdigest()


def main():
    assert os.environ.get('SLURM_JOB_ID') and torch.cuda.is_available()
    torch.set_num_threads(4)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    start = time.perf_counter()
    pp = ROOT / 'protocol/activation_range_v1.json'
    p = json.loads(pp.read_text())
    study = PROJECT / 'integer_qat_20261028/results/study'
    assert sha(study / 'summary.json') == p['formal_QAT_summary_sha256']
    for row in p['models']: assert sha(row['remote_path']) == row['sha256']
    for row in p['code_freeze']: assert sha(row['remote_path']) == row['sha256']
    manifest = PROJECT / 'identity_training/results/input_audit/manifest.json'
    assert sha(manifest) == p['manifest_sha256']
    lookup = {r['relative_path']: r for r in json.loads(manifest.read_text()) if r['split'] == 'train'}
    calibration_path = PROJECT / 'deployment_audit/results/export_audit/ptq_calibration_training_only.json'
    assert sha(calibration_path) == p['calibration_manifest_sha256']
    calibration = json.loads(calibration_path.read_text())
    assert len(calibration) == 64
    out = ROOT / 'results/probe'
    out.mkdir(exist_ok=False)
    deterministic, augmented = BodyTransform(), BodyTransform(augment=True)
    views = {'deterministic': [], 'augmented': []}
    access, input_rows = [], []
    for i, row in enumerate(calibration):
        assert row['split'] == lookup[row['relative_path']]['split'] == 'train'
        path = PROJECT / 'identity_training' / row['relative_path']
        assert sha(path) == row['sha256']
        with Image.open(path) as im:
            im.load()
            image = im.convert('RGB')
        a = deterministic(image)
        seed = p['augmentation_seed_base'] + i
        torch.manual_seed(seed)
        random.seed(seed)
        b = augmented(image)
        views['deterministic'].append(a)
        views['augmented'].append(b)
        access.append({'relative_path': row['relative_path'], 'split': 'train', 'sha256': row['sha256']})
        input_rows.append({'index': i, 'augmentation_seed': seed,
            'deterministic_tensor_sha256': hashlib.sha256(a.numpy().tobytes()).hexdigest(),
            'augmented_tensor_sha256': hashlib.sha256(b.numpy().tobytes()).hexdigest()})
    views = {k: torch.stack(v) for k, v in views.items()}
    old_inputs = np.load(PROJECT / 'qat_study/results/smoke/export_parity_vectors.npz')['inputs']
    assert np.array_equal(views['deterministic'][:8].numpy(), old_inputs)
    save(out / 'training_image_access.json', access)
    save(out / 'input_tensor_hashes.json', input_rows)
    # Keep exactpreselected fixture input images as tensors; all128 hashes kept.
    np.savez_compressed(out / 'fixture_original_inputs.npz', **{k: v[:1].numpy() for k, v in views.items()})
    rows, feature_arrays, layer_rows, fixture_arrays, fixture_records, gates = [], {}, [], {}, [], []
    weight_rows = []
    for source in p['source_models']:
        seed = source['seed']
        assert sha(source['path']) == source['sha256']
        teacher = make_encoder(source['path']).cuda().eval().requires_grad_(False)
        initial_row = next(r for r in p['models'] if r['seed'] == seed and r['condition'] == 'initial_integer')
        qparams_model = restore(source, initial_row)
        qparams = {n: {k: getattr(m, k).clone().cuda() for k in ['sx', 'zx', 'sw', 'sy', 'zy']}
                   for n, m in qparams_model.named_modules() if isinstance(m, TrainableIntegerConv)}
        assert len(qparams) == 52
        teacher_features = {}
        with torch.no_grad():
            for view, images in views.items():
                teacher_features[view] = np.concatenate([F.normalize(teacher(x.cuda()), dim=1).cpu().numpy()
                    for x in images.split(p['batch_size'])])
                feature_arrays[f'seed{seed}_teacher_{view}'] = teacher_features[view]
        for condition in p['conditions']:
            baseline_name = condition if not condition.startswith('QAT_no_') else 'integer_forward_qat'
            row = next(r for r in p['models'] if r['seed'] == seed and r['condition'] == baseline_name)
            model = restore(source, row).cuda()
            before_digest = parameters_digest(model)
            before_weights = weight_digest(model)
            quantized = row['quantized']
            act_clip = condition != 'QAT_no_activation_clipping'
            weight_clip = condition != 'QAT_no_weight_clipping'
            holder = {'view': None, 'first_sample': None, 'totals': {}, 'collect': False}
            names = list(qparams)
            handles = []
            for index, name in enumerate(names):
                module = model.get_submodule(name)
                conv = module.conv if quantized else module
                params = qparams[name]
                raw_w = torch.round(conv.weight / params['sw'].reshape(-1, 1, 1, 1))
                wstat = stats(raw_w, -128, 127).cpu().tolist()
                weight_rows.append({'seed': seed, 'condition': condition, 'module': name,
                                    'elements': wstat[0], 'below': wstat[1], 'above': wstat[2],
                                    'at_min': wstat[3], 'at_max': wstat[4], 'clipping_applied': quantized and weight_clip})
                def add_statistics(label, values):
                    if label not in holder['totals']: holder['totals'][label] = values
                    else: holder['totals'][label] += values
                if quantized:
                    def make_forward(label, layer_index):
                        def forward(self, x):
                            ix = torch.round(x / self.sx) + self.zx.float()
                            iw = torch.round(self.conv.weight / self.sw.reshape(-1, 1, 1, 1))
                            qx = ix.clamp(0, 255) if act_clip else ix
                            qw = iw.clamp(-128, 127) if weight_clip else iw
                            centered = qx - self.zx.float()
                            bound = self.conv.weight.shape[1] * self.conv.weight.shape[2] * self.conv.weight.shape[3] * float(centered.abs().max()) * float(qw.abs().max())
                            assert bound <= np.iinfo(np.int32).max
                            acc = F.conv2d(centered.double(), qw.double(), None, self.conv.stride,
                                           self.conv.padding, self.conv.dilation, self.conv.groups)
                            assert torch.equal(acc, torch.round(acc))
                            raw = acc * self.sx.double()
                            raw = raw * self.sw.double().reshape(1, -1, 1, 1)
                            raw = (raw + self.conv.bias.double().reshape(1, -1, 1, 1)).float()
                            iy = torch.round(raw / self.sy) + self.zy.float()
                            qy = iy.clamp(0, 255) if act_clip else iy
                            value = (qy - self.zy.float()) * self.sy
                            if holder['collect']:
                                add_statistics(label, torch.cat([stats(ix, 0, 255), stats(iy, 0, 255)]))
                            if holder['collect'] and holder['first_sample'] == 0 and layer_index in [0, 20, 51]:
                                key = f's{seed}_{condition}_{holder["view"]}_l{layer_index}'
                                for field, array in [('ix', ix[:1]), ('iw', iw), ('qx', qx[:1]), ('qw', qw),
                                                     ('acc', acc[:1]), ('raw', raw[:1]), ('iy', iy[:1]), ('output', value[:1])]:
                                    fixture_arrays[key + '_' + field] = array.detach().cpu().numpy()
                                fixture_records.append({'key': key, 'seed': seed, 'condition': condition, 'view': holder['view'],
                                    'module': label, 'layer_index': layer_index, 'act_clip': act_clip, 'weight_clip': weight_clip,
                                    'source_state': row, 'stride': self.conv.stride, 'padding': self.conv.padding,
                                    'dilation': self.conv.dilation, 'groups': self.conv.groups})
                            return value
                        return forward
                    module.forward = types.MethodType(make_forward(name, index), module)
                else:
                    def hook(mod, arguments, output, label=name):
                        if not holder['collect']: return
                        params = qparams[label]
                        ix = torch.round(arguments[0] / params['sx']) + params['zx'].float()
                        iy = torch.round(output / params['sy']) + params['zy'].float()
                        add_statistics(label, torch.cat([stats(ix, 0, 255), stats(iy, 0, 255)]))
                    handles.append(module.register_forward_hook(hook))
            if quantized and not condition.startswith('QAT_no_'):
                saved = np.load(study / f'seed{seed}_{baseline_name}/vectors.npz')
                with torch.no_grad():
                    actual = np.concatenate([F.normalize(model(x.cuda()), dim=1).cpu().numpy()
                        for x in views['deterministic'][:8].split(p['batch_size'])])
                difference = float(np.abs(actual - saved['GPU']).max())
                cosine = np.sum(actual.astype(float) * saved['GPU'].astype(float), axis=1) / (np.linalg.norm(actual.astype(float), axis=1) * np.linalg.norm(saved['GPU'].astype(float), axis=1))
                assert difference <= .001 and cosine.min() >= .9999
                gates.append({'seed': seed, 'condition': condition, 'vectors': 8,
                              'maximum_absolute_error': difference, 'minimum_cosine': float(cosine.min()), 'pass': True})
            for view, images in views.items():
                holder.update(view=view, totals={}, collect=True)
                outputs = []
                with torch.no_grad():
                    for first in range(0, 64, p['batch_size']):
                        holder['first_sample'] = first
                        value = F.normalize(model(images[first:first+p['batch_size']].cuda()), dim=1).cpu().numpy()
                        assert np.isfinite(value).all()
                        outputs.append(value)
                z = np.concatenate(outputs)
                feature_arrays[f'seed{seed}_{condition}_{view}'] = z
                target = teacher_features[view]
                cosine = np.sum(z.astype(float) * target.astype(float), axis=1) / (np.linalg.norm(z.astype(float), axis=1) * np.linalg.norm(target.astype(float), axis=1))
                key = f'seed{seed}_{condition}_{view}'
                feature_arrays[key + '_teacher_cosine'] = cosine
                total_in = total_out = clipped_in = clipped_out = 0
                for index, name in enumerate(names):
                    v = holder['totals'][name].cpu().tolist()
                    assert len(v) == 10 and v[1] + v[2] <= v[0] and v[6] + v[7] <= v[5]
                    layer_rows.append({'seed': seed, 'condition': condition, 'view': view, 'module': name, 'layer_index': index,
                        'input_elements': v[0], 'input_below': v[1], 'input_above': v[2], 'input_at_min': v[3], 'input_at_max': v[4],
                        'output_elements': v[5], 'output_below': v[6], 'output_above': v[7], 'output_at_min': v[8], 'output_at_max': v[9],
                        'input_outside_fraction': (v[1]+v[2])/v[0], 'output_outside_fraction': (v[6]+v[7])/v[5],
                        'activation_clipping_applied': quantized and act_clip,
                        'float_statistics_are_potential_range_checks': not quantized})
                    total_in += v[0]
                    clipped_in += v[1] + v[2]
                    total_out += v[5]
                    clipped_out += v[6] + v[7]
                record = {'seed': seed, 'condition': condition, 'view': view, 'images': 64,
                          'weighted_input_outside_fraction': clipped_in / total_in,
                          'weighted_output_outside_fraction': clipped_out / total_out,
                          'mean_teacher_cosine': float(cosine.mean()), 'median_teacher_cosine': float(np.median(cosine)),
                          'mean_teacher_feature_MSE': float(np.mean((z.astype(float)-target.astype(float))**2)),
                          'nondeployable_unbounded_code_control': condition.startswith('QAT_no_')}
                rows.append(record)
                print(json.dumps({'event': 'TRAIN_RANGE_CONDITION', **record}), flush=True)
            assert parameters_digest(model) == before_digest
            assert weight_digest(model) == before_weights
            for h in handles: h.remove()
            del model
            torch.cuda.empty_cache()
        del teacher, qparams_model
        torch.cuda.empty_cache()
    assert len(rows) == 36 and len(layer_rows) == 1872 and len(fixture_records) == 72 and len(gates) == 6
    np.savez_compressed(out / 'feature_vectors.npz', **feature_arrays)
    np.savez_compressed(out / 'arithmetic_fixtures.npz', **fixture_arrays)
    save(out / 'arithmetic_fixture_index.json', fixture_records)
    save(out / 'layer_statistics.json', layer_rows)
    save(out / 'weight_statistics.json', weight_rows)
    save(out / 'baseline_gates.json', gates)
    summary = {'status': 'TRAIN_ONLY_RANGE_COUNTS_AND_FIXED_WEIGHT_CLIPPING_CONTROLS_COMPLETE',
               'job_id': os.environ['SLURM_JOB_ID'], 'protocol_sha256': sha(pp), 'conditions': rows,
               'layer_condition_rows': len(layer_rows), 'source_training_images': 64, 'views_per_image': 2,
               'model_condition_image_forwards': 2304, 'actual_optimizer_updates': 0,
               'representative_arithmetic_fixtures': 72, 'frozen_baseline_regression_gates': gates,
               'validation_or_test_image_reads': 0, 'model_weights_and_qparams_unchanged': True,
               'counterfactuals_are_not_valid_U8S8_models': True, 'FPGA_execution_verified': False,
               'GPU': torch.cuda.get_device_name(0), 'elapsed_s': time.perf_counter()-start, 'whole_goal_complete': False}
    save(out / 'summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ['conditions', 'frozen_baseline_regression_gates']}), flush=True)


if __name__ == '__main__': main()
