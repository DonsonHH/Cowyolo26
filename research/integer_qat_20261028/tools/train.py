from pathlib import Path
import copy, hashlib, json, os, random, sys, time
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
PROJECT = Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT = PROJECT / 'integer_qat_20261028'
sys.path.insert(0, str(PROJECT / 'qat_study/tools'))
sys.path.insert(0, str(PROJECT / 'identity_training/tools'))
sys.path.insert(0, str(PROJECT / 'integer_trainable_20261028/tools'))
from qat_components import make_encoder, fold_batchnorm, insert_quantisers, export_graph, sha, save
from integer_trainable import convert, parameters_digest, TrainableIntegerConv
from smoke import parity as integer_parity, runtime, metric
from training_primitives import BodyTransform, identity_batch, batch_hard_triplet
from identity_metrics import calibrate_threshold, summarise


def seed_all(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def float_parity(model, tensors, directory):
    directory.mkdir(exist_ok=False)
    cpu = copy.deepcopy(model).cpu().eval()
    torch.save(cpu.state_dict(), directory / 'state.pt')
    path = directory / 'packed.onnx'
    export_graph(cpu, path, tensors[0])
    r = runtime(path, 'OFF')
    rows, values, reference = [], [], []
    for i, x in enumerate(tensors[:8]):
        with torch.no_grad(): a = F.normalize(cpu(x), dim=1).numpy()
        b = r.run(None, {'images': x.numpy()})[0]
        rows.append({'vector': i, **metric(a, b)})
        reference.append(a)
        values.append(b)
    np.savez_compressed(directory / 'vectors.npz', inputs=torch.cat(tensors[:8]).numpy(), CPU=np.concatenate(reference), OFF=np.concatenate(values))
    result = {'required_all_vectors_pass': all(r['pass'] for r in rows), 'rows': rows,
              'packed_sha256': sha(path), 'state_sha256': sha(directory / 'state.pt')}
    save(directory / 'summary.json', result)
    return result


def main():
    assert os.environ.get('SLURM_JOB_ID') and torch.cuda.is_available()
    assert __import__('socket').gethostname() != 'mu01'
    torch.set_num_threads(4)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    protocol_path = ROOT / 'protocol/paired_integer_qat_v1.json'
    p = json.loads(protocol_path.read_text())
    admitted = PROJECT / 'integer_trainable_20261028/results'
    assert sha(admitted / 'smoke_v2/summary.json') == p['admitted_smoke_summary_sha256']
    assert sha(admitted / 'independent_verification.json') == p['admitted_independent_verification_sha256']
    assert json.loads((admitted / 'smoke_v2/summary.json').read_text())['status'] == 'ALL_THREE_TRAINABLE_INTEGER_SMOKE_GATES_PASS'
    for row in p['code_freeze']: assert sha(row['remote_path']) == row['sha256']
    out = ROOT / 'results/study'
    out.mkdir(exist_ok=False)
    start = time.perf_counter()
    manifest_path = PROJECT / 'identity_training/results/input_audit/manifest.json'
    assert sha(manifest_path) == p['source_manifest_sha256']
    manifest = json.loads(manifest_path.read_text())
    train = [r for r in manifest if r['split'] == 'train']
    gallery = [r for r in manifest if r['split'] == 'validation_gallery']
    queries = [r for r in manifest if r['split'] == 'validation_query']
    assert (len(train), len(gallery), len(queries)) == (580, 25, 55)
    assert not {r['identity'] for r in train} & {r['identity'] for r in gallery + queries}
    cal_path = PROJECT / 'deployment_audit/results/export_audit/ptq_calibration_training_only.json'
    assert sha(cal_path) == p['calibration_manifest_sha256']
    calibration = json.loads(cal_path.read_text())
    deterministic, augment = BodyTransform(), BodyTransform(augment=True)
    cache, access = {}, []
    def image(row):
        assert row['split'] in ['train', 'validation_gallery', 'validation_query']
        name = row['relative_path']
        if name not in cache:
            path = PROJECT / 'identity_training' / name
            assert sha(path) == row['sha256']
            with Image.open(path) as im:
                im.load()
                cache[name] = im.convert('RGB')
            access.append({'relative_path': name, 'split': row['split'], 'sha256': row['sha256']})
        return cache[name].copy()
    tensors = [deterministic(image(r))[None] for r in calibration]
    g_tensors = [deterministic(image(r))[None].numpy() for r in gallery]
    q_tensors = [deterministic(image(r))[None].numpy() for r in queries]
    ids = sorted({r['identity'] for r in gallery})
    labels = {s: i for i, s in enumerate(sorted({r['identity'] for r in train}))}
    save(out / 'validation_index.json', {'gallery': gallery, 'queries': queries})
    all_results, pair_logs = [], []
    opt = p['training']
    def evaluate(model, seed, name, quantized, updates):
        directory = out / f'seed{seed}_{name}'
        parity = (integer_parity(model, tensors, directory, {'runtime_conditions': ['OFF', 'ALL_disable_quant_qdq', 'ALL_default_diagnostic']})
                  if quantized else float_parity(model, tensors, directory))
        assert parity['required_all_vectors_pass'], 'Actual final export gate failed; preserve artifact and stop before validation'
        r = runtime(directory / 'packed.onnx', 'ALL_disable_quant_qdq' if quantized else 'OFF')
        g = np.concatenate([r.run(None, {'images': x})[0] for x in g_tensors])
        q = np.concatenate([r.run(None, {'images': x})[0] for x in q_tensors])
        similarities = q.astype(float) @ g.astype(float).T
        scores = np.stack([similarities[:, [j for j, row in enumerate(gallery) if row['identity'] == identity]].max(1) for identity in ids], axis=1)
        predictions = []
        for row, values in zip(queries, scores):
            best = int(np.argmax(values))
            predictions.append({'relative_path': row['relative_path'], 'identity': row['identity'],
                                'is_known': row['identity'] in ids, 'predicted_id': ids[best], 'similarity': float(values[best])})
        threshold = calibrate_threshold([r['similarity'] for r in predictions], [r['predicted_id'] for r in predictions],
                                        [r['identity'] for r in predictions], [r['is_known'] for r in predictions])
        for row in predictions: row['accepted'] = row['similarity'] >= threshold['threshold']
        metrics = summarise(predictions)
        np.savez_compressed(directory / 'validation_embeddings.npz', gallery=g, queries=q)
        save(directory / 'predictions.json', predictions)
        save(directory / 'threshold.json', threshold)
        result = {'seed': seed, 'condition': name, 'quantized': quantized, 'updates': updates,
                  'state_sha256': parity['state_sha256'], 'model_path': str(directory / 'packed.onnx'),
                  'model_sha256': parity['packed_sha256'], 'export_gate': parity,
                  'threshold': threshold, 'validation': metrics}
        save(directory / 'result.json', result)
        all_results.append(result)
        print(json.dumps({'event': 'VALIDATION', 'seed': seed, 'condition': name,
                          'C': metrics['known_correct_accepted_C'], 'W': metrics['known_wrong_accepted_W'],
                          'U': metrics['known_rejected_U'], 'unknown_false_accepts': metrics['unknown_false_accepts'],
                          'closed_top1': metrics['known_closed_top1_correct']}), flush=True)
    for source in p['source_models']:
        seed = source['seed']
        seed_all(seed)
        assert sha(source['path']) == source['sha256']
        assert sha(source['integer_initial_state']) == source['integer_initial_state_sha256']
        teacher = make_encoder(source['path']).eval().requires_grad_(False)
        folded, _ = fold_batchnorm(teacher.cpu())
        folded.requires_grad_(True)
        quant, _ = insert_quantisers(folded)
        quant, _ = convert(quant)
        state = torch.load(source['integer_initial_state'], map_location='cpu', weights_only=True)
        for name, value in quant.named_buffers(): value.resize_(state[name].shape)
        quant.load_state_dict(state)
        quant.requires_grad_(True)
        for name, module in quant.named_modules():
            if isinstance(module, TrainableIntegerConv):
                base = folded.get_submodule(name)
                assert torch.equal(base.weight, module.conv.weight) and torch.equal(base.bias, module.conv.bias)
        qdigest = parameters_digest(quant)
        evaluate(folded, seed, 'source_folded_fp32', False, 0)
        evaluate(quant, seed, 'initial_integer', True, 0)
        rng = random.Random(seed)
        schedule = [identity_batch(train, rng, 8, 4) for _ in range(opt['epochs'] * opt['batches_per_epoch'])]
        save(out / f'seed{seed}_schedule.json', {'indices_into_training_rows': schedule, 'source_manifest_sha256': p['source_manifest_sha256']})
        branch_logs = {}
        teacher = teacher.cuda()
        for condition, model, quantized in [('paired_float_continuation', folded, False), ('integer_forward_qat', quant, True)]:
            seed_all(seed)
            student = copy.deepcopy(model).cuda().train()
            optimizer = torch.optim.AdamW(student.parameters(), lr=opt['learning_rate'], weight_decay=opt['weight_decay'])
            batches, history = [], []
            for epoch in range(opt['epochs']):
                losses = []
                for step in range(opt['batches_per_epoch']):
                    indices = schedule[epoch * opt['batches_per_epoch'] + step]
                    rows = [train[j] for j in indices]
                    x_cpu = torch.stack([augment(image(row)) for row in rows])
                    input_sha = hashlib.sha256(x_cpu.numpy().tobytes()).hexdigest()
                    x = x_cpu.cuda()
                    y = torch.tensor([labels[row['identity']] for row in rows], device='cuda')
                    with torch.no_grad(): target = F.normalize(teacher(x), dim=1)
                    optimizer.zero_grad(set_to_none=True)
                    z = F.normalize(student(x), dim=1)
                    loss = (1 - (z * target).sum(1)).mean() + .25 * batch_hard_triplet(z, y, .3)
                    assert torch.isfinite(loss)
                    loss.backward()
                    grads = [v.grad for v in student.parameters()]
                    assert len(grads) == 104 and all(v is not None and torch.isfinite(v).all() for v in grads)
                    optimizer.step()
                    if quantized: assert parameters_digest(student) == qdigest
                    batches.append({'update': len(batches) + 1, 'training_input_sha256': input_sha,
                                    'loss': float(loss.detach()), 'finite_gradient_tensors': len(grads)})
                    losses.append(float(loss.detach()))
                history.append({'epoch': epoch + 1, 'updates': len(batches), 'mean_loss': float(np.mean(losses))})
                save(out / f'seed{seed}_{condition}_history.json', history)
                print(json.dumps({'event': 'EPOCH', 'seed': seed, 'condition': condition, **history[-1]}), flush=True)
            assert len(batches) == 120
            save(out / f'seed{seed}_{condition}_batches.json', batches)
            branch_logs[condition] = batches
            evaluate(student, seed, condition, quantized, len(batches))
            del student, optimizer
            torch.cuda.empty_cache()
        assert [r['training_input_sha256'] for r in branch_logs['paired_float_continuation']] == [r['training_input_sha256'] for r in branch_logs['integer_forward_qat']]
        pair_logs.append({'seed': seed, 'matched_steps': 120, 'all_augmented_input_tensor_hashes_identical': True,
                          'initial_master_weights_and_biases_exactly_equal': True, 'fixed_qparams_unchanged': True})
        del teacher, folded, quant
        torch.cuda.empty_cache()
    assert len(all_results) == 12
    freeze = {'protocol_sha256': sha(protocol_path), 'frozen_at_unix': time.time(),
              'selection': 'All3seeds/fixedlast epoch6, none selected by validation or oldtest',
              'conditions': [{'seed': r['seed'], 'condition': r['condition'], 'model_sha256': r['model_sha256'],
                              'threshold': r['threshold']['threshold']} for r in all_results]}
    save(out / 'all_models_thresholds_frozen.json', freeze)
    save(out / 'image_access_log.json', access)
    summary = {'status': 'TWELVE_CONDITIONS_PAIRED_INTEGER_QAT_DEVELOPMENT_COMPLETE',
               'job_id': os.environ['SLURM_JOB_ID'], 'protocol_sha256': sha(protocol_path),
               'conditions': all_results, 'paired_controls': pair_logs,
               'formal_QAT_updates': 360, 'paired_float_updates': 360,
               'smoke_updates_carried_into_training': 0, 'image_access_count': len(access),
               'validation_reused_and_threshold_calibrated_on_reported_queries': True,
               'old_evaluation_or_future_holdout_images_accessed': 0,
               'freeze_sha256': sha(out / 'all_models_thresholds_frozen.json'),
               'elapsed_s': time.perf_counter() - start, 'GPU': torch.cuda.get_device_name(0),
               'FPGA_execution_verified': False, 'whole_goal_complete': False}
    save(out / 'summary.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ['conditions', 'paired_controls']}), flush=True)


if __name__ == '__main__': main()
