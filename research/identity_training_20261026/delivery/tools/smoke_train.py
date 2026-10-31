"""Two real training updates using training-role images only; state discarded."""
from pathlib import Path
import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
import json,hashlib,random
from PIL import Image
import torch
import torch.nn.functional as F
from torchvision.models import mobilenet_v3_small
from training_primitives import BodyTransform,identity_batch,batch_hard_triplet
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/identity_training')
OUT=ROOT/'results/smoke';OUT.mkdir(parents=True,exist_ok=False)
audit=json.loads((ROOT/'results/input_audit/summary.json').read_text());assert audit['status']=='PASS'
rows=[r for r in json.loads((ROOT/'results/input_audit/manifest.json').read_text()) if r['split']=='train']
torch.manual_seed(26);torch.cuda.manual_seed_all(26);torch.set_num_threads(4)
torch.backends.cudnn.deterministic=True;torch.backends.cudnn.benchmark=False;torch.use_deterministic_algorithms(True)
torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
assert torch.cuda.is_available()
source=mobilenet_v3_small(weights=None)
source.load_state_dict(torch.load(ROOT/'models/mobilenet_v3_small-047dcff4.pth',map_location='cpu',weights_only=True))
model=torch.nn.Sequential(source.features,source.avgpool,torch.nn.Flatten()).train().cuda()
ids=sorted({r['identity'] for r in rows});labels_index={identity:i for i,identity in enumerate(ids)}
classifier=torch.nn.Parameter(torch.randn(len(ids),576,device='cuda')*.01)
optimiser=torch.optim.AdamW(list(model.parameters())+[classifier],lr=1e-4,weight_decay=1e-4)
transform=BodyTransform(augment=True);rng=random.Random(26);losses=[]
first=next(model.parameters());before=first.detach().clone();accessed=[]
for _ in range(2):
    selected=[rows[i] for i in identity_batch(rows,rng)]
    images=[]
    for row in selected:
        assert row['split']=='train';accessed.append(row['relative_path'])
        with Image.open(ROOT/row['relative_path']) as im:images.append(transform(im.convert('RGB')))
    batch=torch.stack(images).cuda();labels=torch.tensor([labels_index[r['identity']] for r in selected],device='cuda')
    optimiser.zero_grad(set_to_none=True);z=F.normalize(model(batch),dim=1)
    loss=F.cross_entropy(16*F.linear(z,F.normalize(classifier,dim=1)),labels)+batch_hard_triplet(z,labels)
    assert torch.isfinite(loss);loss.backward();assert torch.isfinite(first.grad).all() and first.grad.abs().sum()>0
    optimiser.step();losses.append(float(loss.item()))
delta=float((first.detach()-before).abs().max());assert delta>0
record={'status':'PASS','job_id':os.environ['SLURM_JOB_ID'],'updates':2,'losses':losses,'first_weight_max_delta':delta,
        'actual_training_images_only':True,'accessed_training_paths':accessed,'device':torch.cuda.get_device_name(0),
        'scope':'Forward/backward/runtime smoke, not accuracy or convergence; resulting weights are discarded'}
(OUT/'summary.json').write_text(json.dumps(record,indent=2));print(json.dumps({k:v for k,v in record.items() if k!='accessed_training_paths'}),flush=True)
