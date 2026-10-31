"""Actual train-only folding, gradients, 52-weight packing, and ONNX parity gate."""
from pathlib import Path
import copy, json, os, random, sys
import numpy as np
import torch
from PIL import Image
from qat_components import *

PROJECT = Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT = PROJECT/'qat_study'
sys.path.insert(0, str(PROJECT/'identity_training/tools'))
from training_primitives import BodyTransform, identity_batch, batch_hard_triplet


def main():
    torch.set_num_threads(4)
    assert torch.cuda.is_available()
    protocol_path = ROOT/'protocol/qat_v2.json'
    protocol = json.loads(protocol_path.read_text())
    out = ROOT/'results/smoke'; out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((PROJECT/'identity_training/results/input_audit/manifest.json').read_text())
    rows = [r for r in manifest if r['split'] == 'train']
    calibration = json.loads((PROJECT/'deployment_audit/results/export_audit/ptq_calibration_training_only.json').read_text())
    transform = BodyTransform(); tensors = []
    for row in calibration:
        assert row['split'] == 'train'
        path = PROJECT/'identity_training'/row['relative_path']
        assert sha(path) == row['sha256']
        with Image.open(path) as image:
            tensors.append(transform(image.convert('RGB'))[None])
    checkpoint = Path(protocol['source_models'][0]['path'])
    assert sha(checkpoint) == protocol['source_models'][0]['sha256']
    teacher = make_encoder(checkpoint).cuda().eval()
    folded, folds = fold_batchnorm(teacher)
    with torch.no_grad():
        x = torch.cat(tensors[:8]).cuda()
        first = torch.nn.functional.normalize(teacher(x), dim=1)
        second = torch.nn.functional.normalize(folded(x), dim=1)
        fold_error = float((first-second).abs().max())
    assert fold_error < 2e-5
    student, names = insert_quantisers(folded.cpu()); calibrate(student, tensors)
    digest = qparam_digest(student)
    export_graph(student, out/'initial_qat_unpacked.onnx', tensors[0])
    packed = pack_constant_weights(out/'initial_qat_unpacked.onnx', out/'initial_qat_packed.onnx', tensors[0])
    equality = parity(student, out/'initial_qat_unpacked.onnx', out/'initial_qat_packed.onnx', tensors[:8], out)
    save(out/'export_gate.json', equality)
    assert equality['reference_all_pass'], 'Reference QAT/ONNX parity failed; retain vectors and stop before full training'
    # Real optimiser updates, deliberately discarded after smoke validation.
    torch.manual_seed(26); random.seed(26); rng = random.Random(26)
    student = student.cuda().train()
    initial = {k: p.detach().clone() for k,p in student.named_parameters()}
    optimiser = torch.optim.AdamW(student.parameters(), lr=protocol['training']['learning_rate'], weight_decay=1e-4)
    identities = sorted({r['identity'] for r in rows}); mapping = {s:i for i,s in enumerate(identities)}
    logs = []
    for step in range(2):
        selected = [rows[i] for i in identity_batch(rows, rng)]
        images = []
        for row in selected:
            with Image.open(PROJECT/'identity_training'/row['relative_path']) as im:
                images.append(transform(im.convert('RGB')))
        x = torch.stack(images).cuda(); y = torch.tensor([mapping[r['identity']] for r in selected], device='cuda')
        with torch.no_grad(): target = torch.nn.functional.normalize(teacher(x), dim=1)
        optimiser.zero_grad(set_to_none=True)
        z = torch.nn.functional.normalize(student(x), dim=1)
        distillation = (1-(z*target).sum(1)).mean()
        triplet = batch_hard_triplet(z,y,.3)
        loss = distillation + .25*triplet
        assert torch.isfinite(loss); loss.backward()
        grads = [p.grad for p in student.parameters() if p.grad is not None]
        assert len(grads) == len(initial) and all(torch.isfinite(g).all() for g in grads)
        assert any(torch.count_nonzero(g) > 0 for g in grads)
        optimiser.step()
        logs.append({'step':step+1,'loss':float(loss.detach()),'gradient_tensors':len(grads)})
    changes = sum(not torch.equal(initial[k],p.detach()) for k,p in student.named_parameters())
    assert changes > 0 and qparam_digest(student) == digest
    save(out/'summary.json', {'status':'PASS_TRAIN_ONLY_SMOKE', 'job_id':os.environ['SLURM_JOB_ID'],
         'protocol_sha256':sha(protocol_path), 'folded_BN_count':folds, 'fold_max_embedding_error':fold_error,
         'quantised_Conv_count':len(names), 'fake_quantiser_count':156, 'calibration_training_images':len(calibration),
         'packing':packed, 'export_parity':equality, 'real_discarded_updates':logs,
         'parameter_tensors_changed':changes,'qparams_unchanged_after_updates':True,
         'evaluation_or_validation_image_reads':0, 'device':torch.cuda.get_device_name(0)})
    print(json.dumps({'status':'PASS_TRAIN_ONLY_SMOKE','changed':changes,'parity':equality}), flush=True)


if __name__ == '__main__':
    main()
