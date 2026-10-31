from pathlib import Path
from datetime import datetime,timezone
import os,socket,json,hashlib
import torch
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';torch.set_num_threads(2)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def state(path):
    checkpoint=torch.load(path,map_location='cpu',weights_only=False)
    model=checkpoint.get('ema')
    if model is None:model=checkpoint['model']
    return model.state_dict()
rows=[]
for seed in [26,27,28]:
    old=PROJECT/'detector_factorial_20261029/results/training'/('S192_rot90_seed'+str(seed))/'weights/last.pt'
    new=ROOT/'results/training'/('mosaic100_seed'+str(seed))/'weights/last.pt'
    a,b=state(old),state(new);assert a.keys()==b.keys()
    exact=0;maxerror=0.;different=[]
    for key in a:
        x,y=a[key],b[key];assert x.shape==y.shape and x.dtype==y.dtype
        assert torch.isfinite(x).all() and torch.isfinite(y).all()
        if torch.equal(x,y):exact+=1
        else:
            error=float((x.double()-y.double()).abs().max());maxerror=max(maxerror,error);different.append({'key':key,'maximum_error':error})
    rows.append({'seed':seed,'old_checkpoint_sha256':sha(old),'new_checkpoint_sha256':sha(new),'state_tensors':len(a),
        'state_tensors_byte_value_exact':exact,'all_state_tensors_exact':exact==len(a),'maximum_tensor_value_error':maxerror,'different':different})
r={'status':'FRESH_MOSAIC100_CHECKPOINT_STATE_VS_OLD_FIXED192_CONTROLS_AUDITED','created_UTC':datetime.now(timezone.utc).isoformat(),
    'job_id':os.environ['SLURM_JOB_ID'],'rows':rows,'all3_state_dicts_exact':all(r['all_state_tensors_exact'] for r in rows),
    'checkpoint_container_bytes_need_not_match':True,'new_model_forwards':0,'new_training_updates':0,'whole_goal_complete':False}
p=ROOT/'results/control_weight_reproduction.json';assert not p.exists();p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
