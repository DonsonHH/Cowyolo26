"""Fixed six-epoch paired continuation; no test image access or checkpoint selection."""
from pathlib import Path
import copy, hashlib, json, os, random, sys, time
import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F
from qat_components import *

PROJECT = Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT = PROJECT/'qat_study'
sys.path.insert(0, str(PROJECT/'identity_training/tools'))
sys.path.insert(0, str(PROJECT/'deployment_audit/tools'))
from training_primitives import BodyTransform, identity_batch, batch_hard_triplet
from identity_metrics import calibrate_threshold, summarise
from graph_audit import audit_graph


def main():
    start = time.perf_counter()
    out = ROOT/'results/study'; out.mkdir(parents=True, exist_ok=False)
    protocol_path = ROOT/'protocol/qat_v2.json'; protocol = json.loads(protocol_path.read_text())
    smoke = json.loads((ROOT/'results/smoke/summary.json').read_text())
    assert smoke['status'] == 'PASS_TRAIN_ONLY_SMOKE' and smoke['protocol_sha256'] == sha(protocol_path)
    torch.set_num_threads(4)
    torch.backends.cudnn.deterministic = True; torch.backends.cudnn.benchmark = False
    torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    assert torch.cuda.is_available()
    path = PROJECT/'identity_training/results/input_audit/manifest.json'
    assert sha(path) == protocol['manifest_sha256']
    manifest = json.loads(path.read_text())
    train = [r for r in manifest if r['split'] == 'train']
    validation_g = [r for r in manifest if r['split'] == 'validation_gallery']
    validation_q = [r for r in manifest if r['split'] == 'validation_query']
    assert len(train) == 580 and len(validation_g) == 25 and len(validation_q) == 55
    assert not {r['identity'] for r in train}.intersection(r['identity'] for r in validation_g+validation_q)
    calibration_path = PROJECT/'deployment_audit/results/export_audit/ptq_calibration_training_only.json'
    assert sha(calibration_path) == protocol['calibration_manifest_sha256']
    calibration = json.loads(calibration_path.read_text()); assert len(calibration) == 64
    deterministic = BodyTransform(); augment = BodyTransform(augment=True)
    cache = {}; access_log = []
    def image(row):
        assert row['split'] in ['train','validation_gallery','validation_query']
        relative = row['relative_path']
        if relative not in cache:
            path = PROJECT/'identity_training'/relative
            assert sha(path) == row['sha256']
            with Image.open(path) as im:
                im.load(); cache[relative] = im.convert('RGB')
            access_log.append({'relative_path':relative, 'split':row['split'], 'sha256':row['sha256']})
        return cache[relative].copy()
    tensors = [deterministic(image(r))[None] for r in calibration]
    vg_tensors = [deterministic(image(r))[None].numpy() for r in validation_g]
    vq_tensors = [deterministic(image(r))[None].numpy() for r in validation_q]
    train_ids = sorted({r['identity'] for r in train}); labels = {s:i for i,s in enumerate(train_ids)}
    all_results = []; paired_logs = []
    opt = protocol['training']

    def seed_everything(seed):
        random.seed(seed); np.random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)

    def retrieve(g, q):
        ids = sorted({r['identity'] for r in validation_g})
        similarities = q.astype(float) @ g.astype(float).T
        scores = np.stack([similarities[:,[i for i,r in enumerate(validation_g) if r['identity'] == s]].max(1)
                           for s in ids], axis=1)
        rows = []
        for row, values in zip(validation_q, scores):
            i = int(np.argmax(values))
            rows.append({'relative_path':row['relative_path'], 'identity':row['identity'],
                         'is_known':row['identity'] in ids, 'predicted_id':ids[i], 'similarity':float(values[i])})
        threshold = calibrate_threshold([r['similarity'] for r in rows], [r['predicted_id'] for r in rows],
                                       [r['identity'] for r in rows], [r['is_known'] for r in rows])
        for row in rows:
            row['accepted'] = row['similarity'] >= threshold['threshold']
        return rows, threshold, summarise(rows)

    def evaluate(model, directory, *, quantised, metadata):
        directory.mkdir(parents=True, exist_ok=False)
        checkpoint = directory/'encoder_state.pt'
        cpu = copy.deepcopy(model).cpu().eval()
        torch.save(cpu.state_dict(), checkpoint)
        raw_path = directory/('embedding_unpacked.onnx' if quantised else 'embedding_fp32.onnx')
        export_graph(cpu, raw_path, tensors[0])
        packed_path = directory/'embedding_packed_qdq.onnx' if quantised else raw_path
        packing = pack_constant_weights(raw_path, packed_path, tensors[0]) if quantised else None
        equality = parity(cpu, raw_path, packed_path, tensors[:8], directory)
        graph = audit_graph(packed_path)
        # Never discard a failed export. Stop before trusting validation scores.
        save(directory/'export_gate.json', equality)
        assert equality['reference_all_pass'], 'Export parity failed; no validation result is certified'
        runtime = ort_session(packed_path)
        g = np.concatenate([runtime.run(None, {'images':v})[0] for v in vg_tensors])
        q = np.concatenate([runtime.run(None, {'images':v})[0] for v in vq_tensors])
        predictions, threshold, metrics = retrieve(g,q)
        np.savez_compressed(directory/'validation_embeddings.npz', gallery=g, query=q)
        save(directory/'validation_predictions.json', predictions); save(directory/'threshold.json', threshold)
        result = {**metadata, 'model_path':str(packed_path), 'model_sha256':sha(packed_path),
                  'checkpoint_sha256':sha(checkpoint), 'packing':packing, 'graph':graph,
                  'export_parity':equality, 'validation_threshold':threshold, 'validation':metrics}
        save(directory/'summary.json', result); all_results.append(result)
        print(json.dumps({'condition':metadata['condition'], 'seed':metadata['seed'],
                          'validation_C':metrics['known_correct_accepted_C'],
                          'validation_W':metrics['known_wrong_accepted_W'],
                          'validation_unknown_false_accepts':metrics['unknown_false_accepts'],
                          'validation_closed_top1':metrics['known_closed_top1_correct']}), flush=True)

    for source in protocol['source_models']:
        seed = source['seed']; seed_everything(seed)
        assert sha(source['path']) == source['sha256']
        teacher = make_encoder(source['path']).cuda().eval()
        teacher.requires_grad_(False)
        folded, fold_count = fold_batchnorm(teacher.cpu()); teacher = teacher.cuda()
        folded.requires_grad_(True)
        initial, conv_names = insert_quantisers(folded)
        calibrate(initial, tensors)
        qdigest = qparam_digest(initial)
        save(out/f'calibration_seed{seed}.json', {'source':source, 'calibration_rows':calibration,
              'qparam_digest':qdigest, 'folded_BN_count':fold_count, 'Conv_names':conv_names})
        evaluate(folded, out/f'seed{seed}_source_fp32', quantised=False,
                 metadata={'seed':seed,'condition':'source_fp32','updates':0,'source':source})
        evaluate(initial, out/f'seed{seed}_initial_fixed_range_qdq', quantised=True,
                 metadata={'seed':seed,'condition':'initial_fixed_range_qdq','updates':0,'source':source,
                           'qparam_digest':qdigest})
        rng = random.Random(seed)
        schedule = [identity_batch(train,rng,opt['identities_per_batch'],opt['images_per_identity'])
                    for _ in range(opt['epochs']*opt['batches_per_epoch'])]
        save(out/f'training_schedule_seed{seed}.json', {'training_manifest_sha256':protocol['manifest_sha256'],
             'indices_into_training_rows':schedule,'seed':seed})
        branch_logs = {}
        for name, initial_model in [('paired_float_continuation',folded), ('fixed_range_qat',initial)]:
            seed_everything(seed)
            student = copy.deepcopy(initial_model).cuda().train()
            quant_mode(student, fake=True, observe=False)
            initial_parameters = {k:p.detach().clone() for k,p in student.named_parameters()}
            optimiser = torch.optim.AdamW(student.parameters(), lr=opt['learning_rate'], weight_decay=opt['weight_decay'])
            history = []; batch_log = []
            for epoch in range(opt['epochs']):
                losses = []; kd_losses = []; triplets = []
                for step in range(opt['batches_per_epoch']):
                    indices = schedule[epoch*opt['batches_per_epoch']+step]
                    rows = [train[i] for i in indices]
                    x_cpu = torch.stack([augment(image(r)) for r in rows])
                    input_sha = hashlib.sha256(x_cpu.numpy().tobytes()).hexdigest()
                    x = x_cpu.cuda(); y = torch.tensor([labels[r['identity']] for r in rows], device='cuda')
                    with torch.no_grad():
                        target = F.normalize(teacher(x),dim=1)
                    optimiser.zero_grad(set_to_none=True)
                    z = F.normalize(student(x),dim=1)
                    kd = (1-(z*target).sum(1)).mean()
                    triplet = batch_hard_triplet(z,y,.3)
                    loss = kd+.25*triplet
                    assert torch.isfinite(loss); loss.backward()
                    grads = [p.grad for p in student.parameters() if p.grad is not None]
                    assert len(grads) == len(initial_parameters) and all(torch.isfinite(g).all() for g in grads)
                    optimiser.step()
                    batch_log.append({'update':len(batch_log)+1,'training_input_sha256':input_sha,
                                      'loss':float(loss.detach()),'gradient_tensors':len(grads)})
                    losses.append(float(loss.detach())); kd_losses.append(float(kd.detach())); triplets.append(float(triplet.detach()))
                record = {'epoch':epoch+1, 'updates':len(batch_log), 'loss':float(np.mean(losses)),
                          'distillation':float(np.mean(kd_losses)), 'triplet':float(np.mean(triplets))}
                history.append(record)
                save(out/f'{name}_seed{seed}_history.json',history)
                print(json.dumps({'seed':seed,'condition':name,**record}), flush=True)
            changes = sum(not torch.equal(initial_parameters[k],p.detach()) for k,p in student.named_parameters())
            assert changes > 0
            if name == 'fixed_range_qat':
                assert qparam_digest(student) == qdigest
            branch_logs[name] = batch_log
            save(out/f'{name}_seed{seed}_batch_log.json',batch_log)
            evaluate(student, out/f'seed{seed}_{name}', quantised=name=='fixed_range_qat',
                     metadata={'seed':seed,'condition':name,'updates':len(batch_log),'epochs':opt['epochs'],
                               'source':source,'qparam_digest':qdigest if name=='fixed_range_qat' else None,
                               'parameter_tensors_changed':changes,'history':history})
            del student,optimiser,initial_parameters
            torch.cuda.empty_cache()
        a = branch_logs['paired_float_continuation']; b = branch_logs['fixed_range_qat']
        assert [r['training_input_sha256'] for r in a] == [r['training_input_sha256'] for r in b]
        paired_logs.append({'seed':seed,'matched_updates':len(a),'all_augmentation_tensors_bitwise_identical':True})
        del teacher,initial,folded
        torch.cuda.empty_cache()
    assert len(all_results) == 12
    freeze = {'frozen_at_unix':time.time(), 'protocol_sha256':sha(protocol_path),
              'conditions':[{'seed':r['seed'],'condition':r['condition'],'model_path':r['model_path'],
                             'model_sha256':r['model_sha256'],'threshold':r['validation_threshold']['threshold']}
                            for r in all_results],
              'selection':'No best model, checkpoint, or seed selection; fixed final epoch and all conditions reported',
              'holdout_inference_this_stage':False}
    save(out/'all_models_and_thresholds_frozen.json',freeze)
    save(out/'image_access_log.json',access_log)
    save(out/'feature_index.json',{'validation_gallery':validation_g,'validation_query':validation_q})
    result = {'status':'COMPLETED_TRAIN_VALIDATION_ONLY_QAT_DEVELOPMENT', 'job_id':os.environ['SLURM_JOB_ID'],
              'protocol_sha256':sha(protocol_path), 'paired_controls':paired_logs,'conditions':all_results,
              'freeze_sha256':sha(out/'all_models_and_thresholds_frozen.json'),
              'old_evaluation_or_future_holdout_images_accessed':0, 'elapsed_seconds':time.perf_counter()-start,
              'torch':torch.__version__, 'gpu':torch.cuda.get_device_name(0),
              'scope':protocol['scope'],'validation_reused':True,'hardware_execution':False}
    save(out/'summary.json',result)
    print(json.dumps({'status':result['status'],'elapsed_seconds':result['elapsed_seconds']}),flush=True)


if __name__ == '__main__':
    main()
