from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
text=(ROOT/'tools/preflight_v2.py').read_text()
text=text.replace('seed=26;model=YOLO(p[\'source_weights\']);observed=[];start=None','seed=26;model=YOLO(p[\'source_weights\']);observed=[];gradient_audits=[];start=None')
anchor="assert type(t.optimizer).__name__=='AdamW';start=state_digest(t.model)"
assert anchor in text
text=text.replace(anchor,anchor+'''
            original_step=t.optimizer_step
            def checked_step():
                gradients=[v.grad for v in t.model.parameters() if v.grad is not None]
                assert gradients and all(torch.isfinite(v).all() for v in gradients)
                nonzero=sum(bool(torch.count_nonzero(v)) for v in gradients);assert nonzero>0
                gradient_audits.append({'update':len(gradient_audits)+1,'finite_gradient_tensors':len(gradients),'nonzero_gradient_tensors':nonzero})
                original_step()
            t.optimizer_step=checked_step
''')
anchor="'training_batches':2,'actual_discarded_optimizer_steps':2,"
assert anchor in text;text=text.replace(anchor,anchor+"'gradient_audits':gradient_audits,")
text=text.replace("t=model.trainer;assert stopped and", "t=model.trainer;assert len(gradient_audits)==2;assert stopped and")
text=text.replace("target=ROOT/'results/preflight.json'","target=ROOT/'results/preflight_grad.json'")
text=text.replace('48_CPU_CUDA_ROTATION_ORACLES_AND3_REAL_TRAINER_TWO_UPDATE_SMOKES_PASS','48_ROTATION_ORACLES_AND3_REAL_TRAINERS6_FINITE_GRADIENT_UPDATES_PASS')
file=ROOT/'tools/preflight_grad.py';assert not file.exists();file.write_text(text,newline='\n')
slurm=ROOT/'tools/preflight_grad.slurm';assert not slurm.exists();slurm.write_text((ROOT/'tools/preflight_v2.slurm').read_text().replace('tools/preflight_v2.py','tools/preflight_grad.py').replace('cow-factorial-preflight','cow-factorial-gradient').replace('logs/preflight-%j','logs/gradient-%j'),newline='\n')
record={'status':'FROZEN_BEFORE_GRADIENT_PREFLIGHT','created_UTC':datetime.now(timezone.utc).isoformat(),
 'base_protocol_sha256':sha(ROOT/'protocol/training_v4.json'),'script_sha256':sha(file),
 'reason':'Initial6discardedupdatesrecordedfinite_lossesandchangedweights;explicitfinitegradientchecksaddedbeforeformaltraining.',
 'discarded_updates_planned':6,'formal_updates':0}
file=ROOT/'protocol/gradient_gate_v1.json';assert not file.exists();file.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
