from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,subprocess,sys,shutil
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
REMOTE='/share/home/renly/projects/idcoo_research_20261026/async_highres_20261030'
BRIDGE=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
 assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
verification=load(ROOT/'results/independent_verification.json');design=load(ROOT/'protocol/reference_design_v1.json')
payload=ROOT/'reference_payload';payload.mkdir(exist_ok=False);(payload/'input').mkdir();(payload/'tools').mkdir();(payload/'protocol').mkdir()
rows=[]
for run in load(ROOT/'protocol/run_v1.json')['runs']:
 if run['policy']=='foreground_only':continue
 bg=ROOT/'delivery/results'/run['run']/'background'
 for index,job in enumerate(load(bg/'record.json')['jobs']):
  prefix='query'+str(len(rows)).zfill(3);photo=payload/'input'/(prefix+'.png');vector=payload/'input'/(prefix+'.npz')
  shutil.copyfile(bg/job['photo_file'],photo);shutil.copyfile(bg/job['vector_file'],vector)
  rows.append({'run':run['run'],'index':index,'photo_file':photo.relative_to(payload).as_posix(),'vector_file':vector.relative_to(payload).as_posix(),
   'predicted_id':job['predicted_id'],'accepted':job['accepted'],'actual_scores':[job['retrieval_scores_by_registered_ID'][label] for label in design['registered_IDs']]})
assert len(rows)==verification['actual_background_identity_jobs']
save(payload/'input/jobs.json',rows)
shutil.copyfile(PROJECT/'pynq_identity_ncnn_20261029/board_delivery/vectors_results_v3/all_normalized_features.npz',payload/'input/board_gallery.npz')
shutil.copyfile(ROOT/'tools/reference_encoder.py',payload/'tools/reference_encoder.py');shutil.copyfile(ROOT/'tools/reference.slurm',payload/'tools/reference.slurm')
p={**design,'created_UTC':datetime.now(timezone.utc).isoformat(),'design_sha256':sha(ROOT/'protocol/reference_design_v1.json'),
 'query_count':len(rows),'actual_board_results_sha256':sha(ROOT/'results/independent_verification.json'),
 'input_files':[{'file':f.relative_to(payload).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted((payload/'input').rglob('*')) if f.is_file()]}
save(payload/'protocol/reference_v1.json',p);shutil.copyfile(payload/'protocol/reference_v1.json',ROOT/'protocol/reference_v1.json')
e={'created_UTC':datetime.now(timezone.utc).isoformat(),'script_sha256':sha(payload/'tools/reference_encoder.py'),'protocol_sha256':sha(payload/'protocol/reference_v1.json')}
save(payload/'protocol/reference_execution_v1.json',e);shutil.copyfile(payload/'protocol/reference_execution_v1.json',ROOT/'protocol/reference_execution_v1.json')
archive=ROOT/'reference_payload_v1.tar.gz';assert not archive.exists()
files=[f for f in sorted(payload.rglob('*')) if f.is_file()]
with tarfile.open(archive,'w:gz') as tar:
 for f in files:tar.add(f,arcname=f.relative_to(payload).as_posix(),recursive=False)
meta={'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files),'query_photos':len(rows)};save(ROOT/'results/reference_payload_manifest.json',meta)
create=ROOT/'tools/cluster_create.sh'
create.write_text('set -euo pipefail\ntest "$(id -un)" = renly\ntest "$(hostname)" = mu01\ntest "$HOME" = /share/home/renly\nsqueue -u renly\ntest ! -e '+REMOTE+'\nmkdir '+REMOTE+'\n',encoding='utf-8')
subprocess.run([sys.executable,'-X','utf8',str(BRIDGE),'run',str(create),'--output',str(ROOT/'evidence/cluster_create.txt')],check=True)
subprocess.run([sys.executable,'-X','utf8',str(BRIDGE),'put',str(archive),REMOTE+'/reference_payload_v1.tar.gz'],check=True)
script='''set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly
cd REMOTE
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path,PurePosixPath
import tarfile,hashlib,json
root=Path.cwd();a=root/'reference_payload_v1.tar.gz';assert hashlib.sha256(a.read_bytes()).hexdigest()=='DIGEST'
with tarfile.open(a) as tar:
 assert len(tar.getmembers())==MEMBERS
 for m in tar.getmembers():
  name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts
  f=root.joinpath(*name.parts).resolve();assert f.is_relative_to(root) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
p=json.loads((root/'protocol/reference_v1.json').read_text())
for r in p['input_files']:assert hashlib.sha256((root/r['file']).read_bytes()).hexdigest()==r['sha256']
(root/'logs').mkdir(exist_ok=False)
print(json.dumps({'status':'REFERENCE_INPUTS_STAGED_HASHES_VERIFIED','photos':p['query_count']}))
PY
sbatch --parsable tools/reference.slurm
'''.replace('REMOTE',REMOTE).replace('DIGEST',meta['sha256']).replace('MEMBERS',str(meta['members']))
submit=ROOT/'tools/cluster_submit.sh';submit.write_text(script,encoding='utf-8')
subprocess.run([sys.executable,'-X','utf8',str(BRIDGE),'run',str(submit),'--output',str(ROOT/'evidence/reference_submit.txt')],check=True)
print(json.dumps(meta))
