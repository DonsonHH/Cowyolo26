from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,ast
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OLD=PROJECT/'causal_photo_20261030'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for name in ['reference_encoder.py','reference.slurm','stage_reference.py']:
 source=(OLD/'tools'/name).read_text(encoding='utf-8').replace('/causal_photo_20261030','/async_highres_20261030')
 f=ROOT/'tools'/name;assert not f.exists()
 if name.endswith('.slurm'):f.write_bytes(source.encode('utf-8'))
 else:f.write_text(source,encoding='utf-8')
design=json.loads((OLD/'protocol/reference_design_v1.json').read_text(encoding='utf-8'))
design.update({'status':'FROZEN_REUSE_NUMERIC_GATES_BEFORE_ASYNC_QUERY_REFERENCE','created_UTC':datetime.now(timezone.utc).isoformat(),
 'source_prior_design_sha256':sha(OLD/'protocol/reference_design_v1.json'),'all_actual_queries_including_repeats':True,'score_or_threshold_tuning':False})
f=ROOT/'protocol/reference_design_v1.json';assert not f.exists();f.write_text(json.dumps(design,indent=2)+'\n',encoding='utf-8')
source=(OLD/'tools/verify_reference.py').read_text(encoding='utf-8')
source=source.replace("s['job_id']=='130642'","s['job_id'] in (ROOT/'evidence/reference_submit.txt').read_text(encoding='utf-8').splitlines()")
source=source.replace("'REFERENCE_ARCHIVE_ALL69_TORCH_FEATURES_AND78_RETRIEVALS_SEPARATELY_CHECKED'","'REFERENCE_ARCHIVE_ALL_ACTUAL_QUERIES_AND_GALLERY_SEPARATELY_CHECKED'")
f=ROOT/'tools/verify_reference.py';assert not f.exists();f.write_text(source,encoding='utf-8');ast.parse(source)
print(json.dumps({'reference_numeric_gates_reused':True,'threshold_changed':False,'server_input_images_not_yet_staged':True}))
