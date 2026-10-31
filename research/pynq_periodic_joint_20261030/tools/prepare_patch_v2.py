from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,ast
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
backend=(ROOT/'tools/background_worker.py').read_text().replace('ncnn_encoder_v2','ncnn_encoder_v3').replace('vectors_results_v2','vectors_results_v3')
backfile=ROOT/'tools/background_worker_v2.py';assert not backfile.exists();backfile.write_text(backend,newline='\n');ast.parse(backend)
front=(ROOT/'tools/board_periodic.py').read_text().replace('from background_worker import','from background_worker_v2 import').replace('vectors_results_v2','vectors_results_v3')
frontfile=ROOT/'tools/board_periodic_v2.py';frontfile.write_text(front,newline='\n');ast.parse(front)
p=load(ROOT/'protocol/run_template_v1.json');p.update({'status':'FROZEN_PILLOW_GEOMETRY_CORRECTION_BEFORE_ANY_PERIODIC_EXECUTION',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'previous_template_sha256':sha(ROOT/'protocol/run_template_v1.json'),
 'identity_vector_gate_version':3,'identity_preprocessing':'SamePillow11roundinggeometryasfrozenservertransform;globalboardPillowunchanged.',
 'identity_vector_protocol_sha256':sha(PROJECT/'pynq_identity_ncnn_20261029/protocol/board_vectors_v3.json'),
 'periodic_inputs_model_threshold_sampling_policy_unchanged':True,'previous_periodic_execution_started':False})
p['payload_files'].extend([{'file':f.name,'bytes':f.stat().st_size,'sha256':sha(f)} for f in [backfile,frontfile]])
protocol=ROOT/'protocol/run_template_v2.json';protocol.write_text(json.dumps(p,indent=2)+'\n')
archive=ROOT/'board_patch_v2.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for source,name in [(backfile,backfile.name),(frontfile,frontfile.name),(protocol,'protocol_template_v2.json')]:tar.add(source,arcname=name,recursive=False)
meta={'sha256':sha(archive),'bytes':archive.stat().st_size,'members':3,'protocol_template_sha256':sha(protocol)}
(ROOT/'evidence/patch_v2.json').write_text(json.dumps(meta,indent=2)+'\n')
launch=(ROOT/'tools/launch_board.sh').read_text()
launch=launch.replace('vectors_results_v2','vectors_results_v3').replace('ncnn_encoder_v2','ncnn_encoder_v3')
launch=launch.replace("p=json.loads((root/'protocol_template.json').read_text());assert sha(root/'protocol_template.json')=='", "p=json.loads((root/'protocol_template.json').read_text());assert sha(root/'protocol_template.json')=='")
marker="roots=[identity/'libcow_encoder_v2.so'";assert marker in launch
index=launch.index(marker)
patch='''patch=root/'patch_v2.tar.gz';assert sha(patch)=='DIGEST'
with tarfile.open(patch) as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['background_worker_v2.py','board_periodic_v2.py','protocol_template_v2.json']
  f=root/m.name;assert not f.exists();f.write_bytes(tar.extractfile(m).read())
assert sha(root/'protocol_template_v2.json')=='NEWPROTO'
p=json.loads((root/'protocol_template_v2.json').read_text())
'''.replace('DIGEST',meta['sha256']).replace('NEWPROTO',meta['protocol_template_sha256'])
launch=launch[:index]+patch+launch[index:]
launch=launch.replace("str(root/'board_periodic.py')","str(root/'board_periodic_v2.py')")
(ROOT/'tools/launch_board_v2.sh').write_text(launch,newline='\n');print(json.dumps(meta))
