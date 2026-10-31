"""Reproduce first backward failure without taking any optimizer step."""
from pathlib import Path
import copy, json, os, random, sys
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
PROJECT = Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT = PROJECT / 'integer_trainable_20261028'
sys.path.insert(0, str(PROJECT / 'qat_study/tools'))
sys.path.insert(0, str(PROJECT / 'identity_training/tools'))
from qat_components import make_encoder, fold_batchnorm, insert_quantisers, save, sha
from integer_trainable import convert
from training_primitives import BodyTransform, identity_batch, batch_hard_triplet


def main():
    assert os.environ.get('SLURM_JOB_ID') and torch.cuda.is_available()
    torch.set_num_threads(4)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    p = json.loads((ROOT / 'protocol/trainable_integer_smoke_v1.json').read_text())
    source = p['source_models'][0]
    state = torch.load(ROOT / 'results/smoke/seed26_initial/state.pt', map_location='cpu', weights_only=True)
    teacher = make_encoder(source['path']).cuda().eval().requires_grad_(False)
    template, _ = fold_batchnorm(make_encoder(source['path']))
    template, _ = insert_quantisers(template)
    template, _ = convert(template)
    for name, buffer in template.named_buffers():
        buffer.resize_(state[name].shape)
    template.load_state_dict(state)
    manifest_path = PROJECT / 'identity_training/results/input_audit/manifest.json'
    assert sha(manifest_path) == p['manifest_sha256']
    train = [r for r in json.loads(manifest_path.read_text()) if r['split'] == 'train']
    labels = {s: i for i, s in enumerate(sorted({r['identity'] for r in train}))}
    indices = identity_batch(train, random.Random(26), 8, 4)
    transform = BodyTransform()
    tensors = []
    for j in indices:
        row = train[j]
        path = PROJECT / 'identity_training' / row['relative_path']
        assert sha(path) == row['sha256']
        with Image.open(path) as image:
            tensors.append(transform(image.convert('RGB')))
    x = torch.stack(tensors).cuda()
    y = torch.tensor([labels[train[j]['identity']] for j in indices], device='cuda')
    with torch.no_grad():
        target = F.normalize(teacher(x), dim=1)
    out = ROOT / 'results/backward_probe'
    out.mkdir(exist_ok=False)
    rows = []
    for condition in ['KD_only', 'triplet_default_only', 'combined_original', 'triplet_direct_distance_only']:
        student = copy.deepcopy(template).cuda().train()
        z = F.normalize(student(x), dim=1)
        if condition == 'KD_only':
            loss = (1 - (z * target).sum(1)).mean()
        elif condition == 'combined_original':
            loss = (1 - (z * target).sum(1)).mean() + .25 * batch_hard_triplet(z, y, .3)
        elif condition == 'triplet_default_only':
            loss = batch_hard_triplet(z, y, .3)
        else:
            distance = torch.cdist(z, z, p=2, compute_mode='donot_use_mm_for_euclid_dist')
            same = y[:, None] == y[None, :]
            positive = same & ~torch.eye(len(y), dtype=torch.bool, device='cuda')
            hardest_p = distance.masked_fill(~positive, -torch.inf).max(1).values
            hardest_n = distance.masked_fill(same, torch.inf).min(1).values
            loss = F.relu(hardest_p - hardest_n + .3).mean()
        loss.backward()
        missing, nonfinite, frozen = [], [], []
        for name, parameter in student.named_parameters():
            if not parameter.requires_grad:
                frozen.append(name)
            if parameter.grad is None:
                missing.append(name)
            elif not torch.isfinite(parameter.grad).all():
                nonfinite.append({'name': name, 'nonfinite_elements': int((~torch.isfinite(parameter.grad)).sum())})
        row = {'condition': condition, 'loss': float(loss.detach()), 'parameter_tensors': len(list(student.parameters())),
               'missing_gradient_tensors': missing, 'frozen_parameter_tensors': frozen, 'nonfinite_gradient_tensors': nonfinite,
               'finite_nonzero_gradient_tensors': sum(v.grad is not None and bool(torch.isfinite(v.grad).all()) and bool(torch.count_nonzero(v.grad)) for v in student.parameters())}
        rows.append(row)
        print(json.dumps(row), flush=True)
    save(out / 'summary.json', {'status': 'FIRST_BACKWARD_FAILURE_LOSS_COMPONENT_CONTROLS_COMPLETE', 'job_id': os.environ['SLURM_JOB_ID'],
         'seed': 26, 'training_indices': indices, 'source_initial_state_sha256': sha(ROOT / 'results/smoke/seed26_initial/state.pt'),
         'conditions': rows, 'optimizer_steps': 0, 'formal_QAT_updates': 0, 'whole_goal_complete': False})


if __name__ == '__main__':
    main()
