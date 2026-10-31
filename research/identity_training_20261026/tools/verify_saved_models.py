"""Reload saved checkpoints on CPU and compare held-out validation embeddings."""
from pathlib import Path
import hashlib,json,os
import numpy as np
from PIL import Image
import torch
from torchvision.models import mobilenet_v3_small,MobileNet_V3_Small_Weights
from training_primitives import BodyTransform
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/identity_training');STUDY=ROOT/'results/study'
OUT=ROOT/'results/checkpoint_verification';OUT.mkdir(parents=True,exist_ok=False)
summary=json.loads((STUDY/'summary.json').read_text());index=json.loads((STUDY/'feature_index.json').read_text())
freeze_path=STUDY/'all_models_and_thresholds_frozen.json'
assert hashlib.sha256(freeze_path.read_bytes()).hexdigest()==summary['final_freeze_sha256']
torch.set_num_threads(4);checks=[]
for condition in summary['conditions']:
    path=Path(condition['checkpoint']);assert hashlib.sha256(path.read_bytes()).hexdigest()==condition['checkpoint_sha256']
    base=mobilenet_v3_small(weights=None)
    if condition['seed'] is None:base.load_state_dict(torch.load(path,map_location='cpu',weights_only=True))
    model=torch.nn.Sequential(base.features,base.avgpool,torch.nn.Flatten()).eval()
    if condition['seed'] is not None:model.load_state_dict(torch.load(path,map_location='cpu',weights_only=True))
    transform=MobileNet_V3_Small_Weights.IMAGENET1K_V1.transforms() if condition['preprocess']=='official' else BodyTransform()
    saved=np.load(STUDY/condition['name']/'validation_embeddings.npz')
    for split,key in [('validation_gallery','gallery'),('validation_query','query')]:
        rows=index[split];vectors=[]
        with torch.inference_mode():
            for i in range(0,len(rows),32):
                batch=[]
                for r in rows[i:i+32]:
                    with Image.open(ROOT/r['relative_path']) as im:batch.append(transform(im.convert('RGB')))
                vectors.append(torch.nn.functional.normalize(model(torch.stack(batch)),dim=1).numpy())
        actual=np.concatenate(vectors);expected=saved[key]
        difference=float(np.abs(actual-expected).max())
        assert np.allclose(actual,expected,rtol=1e-4,atol=1e-5),(condition['name'],key,difference)
        checks.append({'condition':condition['name'],'split':split,'images':len(rows),'max_absolute_cpu_vs_saved_gpu_embedding_error':difference,'allclose_passed':True})
record={'status':'PASS','job_id':os.environ['SLURM_JOB_ID'],'device':'CPU','checks':checks,
        'scope':'Checkpoint reload and CPU-vs-GPU validation numerical agreement only; no board mapping or independent reference-label confirmation'}
(OUT/'summary.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2),flush=True)
