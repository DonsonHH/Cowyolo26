from pathlib import Path
import copy, hashlib, json, os, random, sys, time
import numpy as np
import torch
import torch.nn.functional as F
import onnxruntime as ort
from PIL import Image
PROJECT = Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT = PROJECT / 'integer_trainable_20261028'
sys.path.insert(0, str(PROJECT / 'qat_study/tools'))
sys.path.insert(0, str(PROJECT / 'identity_training/tools'))
from qat_components import make_encoder, fold_batchnorm, insert_quantisers, calibrate, sha, save
from training_primitives import BodyTransform, identity_batch, batch_hard_triplet
from integer_trainable import convert, gradient_controls, parameters_digest
from export_integer import export, pack


def runtime(source, condition):
    option = ort.SessionOptions()
    option.intra_op_num_threads = 2
    option.inter_op_num_threads = 1
    option.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL if condition == 'OFF' else ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    if condition == 'ALL_disable_quant_qdq':
        option.add_session_config_entry('session.disable_quant_qdq', '1')
    return ort.InferenceSession(str(source) if isinstance(source, Path) else source,
                                sess_options=option, providers=['CPUExecutionProvider'])


def metric(a, b):
    maximum = float(np.max(np.abs(a - b)))
    aa, bb = a.astype(np.float64), b.astype(np.float64)
    cosine = float(np.sum(aa * bb) / (np.linalg.norm(aa) * np.linalg.norm(bb)))
    return {'maximum_absolute_error': maximum, 'cosine': cosine, 'pass': maximum <= .001 and cosine >= .9999}


def parity(model, tensors, folder, protocol):
    folder.mkdir(exist_ok=False)
    cpu = copy.deepcopy(model).cpu().eval()
    gpu = copy.deepcopy(model).cuda().eval()
    torch.save(cpu.state_dict(), folder / 'state.pt')
    export(cpu, folder / 'unpacked.onnx', tensors[0])
    packing = pack(folder / 'unpacked.onnx', folder / 'packed.onnx', cpu, tensors[0], runtime)
    raw = runtime(folder / 'unpacked.onnx', 'OFF')
    sessions = {name: runtime(folder / 'packed.onnx', name) for name in protocol['runtime_conditions']}
    arrays = {k: [] for k in ['CPU', 'GPU', 'unpacked'] + protocol['runtime_conditions']}
    rows = []
    for i, tensor in enumerate(tensors[:8]):
        with torch.no_grad():
            a = F.normalize(cpu(tensor), dim=1).numpy()
            g = F.normalize(gpu(tensor.cuda()), dim=1).cpu().numpy()
        b = raw.run(None, {'images': tensor.numpy()})[0]
        values = {name: r.run(None, {'images': tensor.numpy()})[0] for name, r in sessions.items()}
        packing_error = float(np.max(np.abs(b - values['OFF'])))
        row = {'vector': i, 'GPU_CPU': metric(a, g), 'packing_max_error': packing_error,
               'runtime': {name: metric(a, value) for name, value in values.items()}}
        row['required_gate_pass'] = (row['GPU_CPU']['pass'] and packing_error <= 1e-6
            and row['runtime']['OFF']['pass'] and row['runtime']['ALL_disable_quant_qdq']['pass'])
        rows.append(row)
        for key, value in {'CPU': a, 'GPU': g, 'unpacked': b, **values}.items():
            arrays[key].append(value)
    np.savez_compressed(folder / 'vectors.npz', inputs=torch.cat(tensors[:8]).numpy(), **{k: np.concatenate(v) for k, v in arrays.items()})
    summary = {'required_all_vectors_pass': all(r['required_gate_pass'] for r in rows),
               'CPU_GPU_passes': sum(r['GPU_CPU']['pass'] for r in rows),
               'runtime_passes': {name: sum(r['runtime'][name]['pass'] for r in rows) for name in sessions},
               'maximum_packing_error': max(r['packing_max_error'] for r in rows),
               'packing': packing, 'packed_sha256': sha(folder / 'packed.onnx'), 'state_sha256': sha(folder / 'state.pt'),
               'rows': rows}
    save(folder / 'summary.json', summary)
    del gpu, cpu
    torch.cuda.empty_cache()
    return summary


def main():
    assert os.environ.get('SLURM_JOB_ID') and torch.cuda.is_available()
    assert __import__('socket').gethostname() != 'mu01'
    start = time.perf_counter()
    torch.set_num_threads(4)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    protocol_path = ROOT / 'protocol/trainable_integer_smoke_v1.json'
    p = json.loads(protocol_path.read_text())
    out = ROOT / 'results/smoke'
    out.mkdir(exist_ok=False)
    controls = gradient_controls('cpu') + gradient_controls('cuda')
    save(out / 'gradient_controls.json', controls)
    manifest_path = PROJECT / 'identity_training/results/input_audit/manifest.json'
    assert sha(manifest_path) == p['manifest_sha256']
    manifest = json.loads(manifest_path.read_text())
    train = [r for r in manifest if r['split'] == 'train']
    assert len(train) == 580
    calibration_path = PROJECT / 'deployment_audit/results/export_audit/ptq_calibration_training_only.json'
    assert sha(calibration_path) == p['calibration_manifest_sha256']
    calibration = json.loads(calibration_path.read_text())
    assert len(calibration) == 64 and all(r['split'] == 'train' for r in calibration)
    transform = BodyTransform()
    cache, access = {}, []
    def image(row):
        assert row['split'] == 'train'
        path = PROJECT / 'identity_training' / row['relative_path']
        if row['relative_path'] not in cache:
            assert sha(path) == row['sha256']
            with Image.open(path) as im:
                im.load()
                cache[row['relative_path']] = im.convert('RGB')
            access.append({'relative_path': row['relative_path'], 'split': 'train', 'sha256': row['sha256']})
        return cache[row['relative_path']].copy()
    tensors = [transform(image(r))[None] for r in calibration]
    previous = np.load(PROJECT / 'qat_study/results/smoke/export_parity_vectors.npz')
    assert np.array_equal(torch.cat(tensors[:8]).numpy(), previous['inputs'])
    prepared, results = {}, []
    for source in p['source_models']:
        seed = source['seed']
        assert sha(source['path']) == source['sha256']
        teacher = make_encoder(source['path']).eval()
        folded, _ = fold_batchnorm(teacher)
        original, _ = insert_quantisers(folded)
        calibrate(original, tensors)
        student, names = convert(original)
        digest = parameters_digest(student)
        initial = parity(student, tensors, out / f'seed{seed}_initial', p)
        prepared[seed] = (student, teacher, digest)
        row = {'seed': seed, 'source': source, 'integer_Conv_count': len(names), 'initial': initial,
               'frozen_qparams_sha256': digest, 'discarded_smoke_updates': 0, 'post_update': None}
        results.append(row)
        save(out / 'progress.json', results)
        print(json.dumps({'event': 'ALL_SEED_INITIAL_GATE', 'seed': seed,
                          'required_all_vectors_pass': initial['required_all_vectors_pass'],
                          'runtime_passes': initial['runtime_passes'], 'CPU_GPU_passes': initial['CPU_GPU_passes']}), flush=True)
    all_initial = all(r['initial']['required_all_vectors_pass'] for r in results)
    labels = {s: i for i, s in enumerate(sorted({r['identity'] for r in train}))}
    for row in results:
        if not all_initial:
            continue
        seed = row['seed']
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        random.seed(seed)
        np.random.seed(seed)
        student, teacher, digest = prepared[seed]
        student = student.cuda().train()
        teacher = teacher.cuda().eval().requires_grad_(False)
        initial_parameters = {k: v.detach().clone() for k, v in student.named_parameters()}
        optimiser = torch.optim.AdamW(student.parameters(), lr=p['training']['learning_rate'], weight_decay=p['training']['weight_decay'])
        rng = random.Random(seed)
        updates = []
        for step in range(p['actual_discarded_smoke_updates_each']):
            indices = identity_batch(train, rng, 8, 4)
            selected = [train[j] for j in indices]
            x_cpu = torch.stack([transform(image(r)) for r in selected])
            x = x_cpu.cuda()
            y = torch.tensor([labels[r['identity']] for r in selected], device='cuda')
            with torch.no_grad():
                target = F.normalize(teacher(x), dim=1)
            optimiser.zero_grad(set_to_none=True)
            z = F.normalize(student(x), dim=1)
            loss = (1 - (z * target).sum(1)).mean() + .25 * batch_hard_triplet(z, y, .3)
            assert torch.isfinite(loss)
            loss.backward()
            grads = {k: v.grad for k, v in student.named_parameters()}
            assert len(grads) == len(initial_parameters) and all(g is not None and torch.isfinite(g).all() for g in grads.values())
            assert any(torch.count_nonzero(g) for g in grads.values())
            optimiser.step()
            assert parameters_digest(student) == digest
            updates.append({'step': step + 1, 'indices_into_training_rows': indices,
                            'input_sha256': hashlib.sha256(x_cpu.numpy().tobytes()).hexdigest(),
                            'loss': float(loss.detach()), 'finite_gradient_tensors': len(grads),
                            'nonzero_gradient_tensors': sum(bool(torch.count_nonzero(g)) for g in grads.values())})
        changed = [k for k, v in student.named_parameters() if not torch.equal(initial_parameters[k], v.detach())]
        assert changed and parameters_digest(student) == digest
        row['discarded_smoke_updates'] = len(updates)
        row['updates'] = updates
        row['changed_parameter_tensors'] = len(changed)
        row['post_update'] = parity(student, tensors, out / f'seed{seed}_post2updates', p)
        save(out / 'progress.json', results)
        print(json.dumps({'event': 'ALL_SEED_POST_UPDATE_GATE', 'seed': seed,
                          'updates': len(updates), 'changed_parameter_tensors': len(changed),
                          'required_all_vectors_pass': row['post_update']['required_all_vectors_pass'],
                          'runtime_passes': row['post_update']['runtime_passes']}), flush=True)
        del student, teacher, optimiser, initial_parameters
        torch.cuda.empty_cache()
    save(out / 'training_image_access_log.json', access)
    save(out / 'calibration_manifest.json', calibration)
    summary = {'status': 'ALL_THREE_TRAINABLE_INTEGER_SMOKE_GATES_PASS' if all_initial and all(r['post_update']['required_all_vectors_pass'] for r in results) else 'TRAINABLE_INTEGER_SMOKE_GATE_FAIL_RETAIN_ALL_RESULTS',
               'job_id': os.environ['SLURM_JOB_ID'], 'protocol_sha256': sha(protocol_path),
               'source_training_manifest_sha256': p['manifest_sha256'], 'source_calibration_manifest_sha256': p['calibration_manifest_sha256'],
               'all_initial_required_gates_pass': all_initial, 'gradient_controls': controls, 'seeds': results,
               'actual_discarded_smoke_updates': sum(r['discarded_smoke_updates'] for r in results),
               'formal_QAT_updates': 0, 'source_input_vectors_unchanged': True,
               'validation_or_holdout_image_reads': 0, 'image_access_count': len(access),
               'torch': torch.__version__, 'ORT': ort.__version__, 'GPU': torch.cuda.get_device_name(0),
               'elapsed_s': time.perf_counter() - start, 'FPGA_execution_verified': False,
               'whole_goal_complete': False}
    save(out / 'summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ['seeds', 'gradient_controls']}), flush=True)


if __name__ == '__main__':
    main()
