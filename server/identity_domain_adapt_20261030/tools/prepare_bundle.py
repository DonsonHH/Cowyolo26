from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,tarfile

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
assert json.loads((ROOT/'results/input_admission.json').read_text())['admitted']
for source,name in [('identity_training_20261026/tools/training_primitives.py','frozen_training_primitives.py'),
                    ('identity_training_20261026/tools/identity_metrics.py','frozen_identity_metrics.py'),
                    ('pynq_identity_ncnn_20261029/tools/ncnn_encoder_v3.py','frozen_body_tensor.py')]:
 dest=ROOT/'tools'/name;assert not dest.exists();dest.write_bytes((PROJECT/source).read_bytes())
for path in(ROOT/'tools').glob('*.py'):ast.parse(path.read_text(encoding='utf-8'))
paths=sorted([path for directory in['tools','protocol','input']for path in(ROOT/directory).rglob('*')if path.is_file()]+[ROOT/'results/acquisition.json',ROOT/'results/input_admission.json',ROOT/'计划与验收.md'])
execution={'created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(ROOT/'protocol/run_v1.json'),
           'files_sha256':{path.relative_to(ROOT).as_posix():sha(path)for path in paths},
           'code_hashes':{path.relative_to(ROOT).as_posix():sha(path)for path in paths if path.suffix in['.py','.slurm']},'training_updates_before_freeze':0}
p=ROOT/'protocol/execution_v1.json';assert not p.exists();p.write_text(json.dumps(execution,indent=2)+'\n');paths.append(p)
archive=ROOT/'domain_input_v1.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz')as tar:
 for path in paths:tar.add(path,arcname=path.relative_to(ROOT).as_posix(),recursive=False)
record={'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(paths),'protocol_sha256':execution['protocol_sha256'],'new_model_forwards':0}
p=ROOT/'evidence/input_bundle.json';assert not p.exists();p.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
