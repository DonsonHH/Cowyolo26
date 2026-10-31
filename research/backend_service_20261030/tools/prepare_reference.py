from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,ast
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OLD=PROJECT/'async_highres_20261030'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for name in ['reference_encoder.py','stage_reference.py','verify_reference.py']:
 text=(OLD/'tools'/name).read_text(encoding='utf-8').replace('/async_highres_20261030','/backend_service_20261030')
 if name=='verify_reference.py':text=text.replace('reference_submit_repaired.txt','reference_submit.txt')
 f=ROOT/'tools'/name;assert not f.exists();ast.parse(text);f.write_text(text,encoding='utf-8')
text=(OLD/'tools/reference_lf.slurm').read_text(encoding='utf-8').replace('/async_highres_20261030','/backend_service_20261030')
f=ROOT/'tools/reference.slurm';assert not f.exists();f.write_bytes(text.encode('utf-8'));assert b'\r\n' not in f.read_bytes()
p=json.loads((OLD/'protocol/reference_design_v1.json').read_text(encoding='utf-8'));p.update({'status':'FROZEN_PRIOR_NUMERIC_GATES_FOR_BACKEND_SERVICE_REFERENCE','created_UTC':datetime.now(timezone.utc).isoformat(),'source_prior_design_sha256':sha(OLD/'protocol/reference_design_v1.json'),'score_or_threshold_tuning':False})
f=ROOT/'protocol/reference_design_v1.json';assert not f.exists();f.write_text(json.dumps(p,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'same_reference_checkpoint_and_numeric_gates':True,'batch_line_endings_LF':True}))
