from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];Q=ROOT/'delivery/results/export_v2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
groups=load(ROOT/'input/images.json');manifest=load(Q/'vector_manifest.json');files={};rows=[];references={}
for row in manifest:
 group=row['group'];i=row['index'];image=groups[group][i];source=Path(image['local_path']);assert sha(source)==image['sha256']
 vector=Q/row['file'];assert sha(vector)==row['sha256']
 with np.load(vector) as a:references.setdefault(group,[]).append(a['Torch_normalized'])
 image_name='images/'+row['name']+source.suffix;files[image_name]=source;files[row['file']]=vector
 rows.append({**row,'image_file':image_name,'image_sha256':sha(source)})
assert len(rows)==132
vectors=ROOT/'input/board_vector_manifest.json';assert not vectors.exists();vectors.write_text(json.dumps(rows,indent=2)+'\n')
reference=ROOT/'input/reference_features.npz';np.savez_compressed(reference,**{k:np.stack(v) for k,v in references.items()})
for source,name in [(vectors,'vector_manifest.json'),(ROOT/'input/images.json','image_groups.json'),(reference,'reference_features.npz'),
                    (ROOT/'tools/ncnn_encoder.py','ncnn_encoder.py'),(ROOT/'tools/board_vectors.py','board_vectors.py')]:files[name]=source
p=load(ROOT/'protocol/encoder_v1.json');proto={'status':'FROZEN_BEFORE_ACTUAL132_ARM_ENCODER_VECTORS','created_UTC':datetime.now(timezone.utc).isoformat(),
 'encoder_protocol_sha256':sha(ROOT/'protocol/encoder_v1.json'),'encoder_checkpoint_sha256':p['encoder_condition']['checkpoint_sha256'],
 'max_normalized_embedding_absolute_error':p['max_normalized_embedding_absolute_error'],
 'maximum_1_minus_cosine_error':p['maximum_1_minus_cosine_error'],'Pillow_preprocessing_max_absolute_tolerance':1e-6,
 'registered_IDs':p['registered_IDs'],'fixed_threshold':p['fixed_threshold'],'threads':1,'model_vectors':132,'warmups':2,
 'old_gallery_leakage_control_only':True,'new_gallery_retrospective_to_Aug14':True,'real_event_ID_accuracy_proven':False,
 'whole_goal_complete':False,'files':[{'file':name,'sha256':sha(file),'bytes':file.stat().st_size} for name,file in sorted(files.items())]}
protocol=ROOT/'protocol/board_vectors_v1.json';assert not protocol.exists();protocol.write_text(json.dumps(proto,indent=2)+'\n');files['vectors_protocol.json']=protocol
archive=ROOT/'board_vectors_payload.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for name,file in sorted(files.items()):tar.add(file,arcname=name,recursive=False)
meta={'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files),'protocol_sha256':sha(protocol)}
(ROOT/'evidence/board_vectors_payload.json').write_text(json.dumps(meta,indent=2)+'\n')
script='''set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess,sys,os
root=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029')
t=json.loads((root/'build_terminal.json').read_text());assert t['success'] and not (Path('/proc')/str(t['PID'])).exists()
assert not (root/'vectors_launch.json').exists() and not (root/'vectors_results').exists()
archive=root/'vectors_payload.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
with tarfile.open(archive) as tar:
 assert len(tar.getmembers())==MEMBERS
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(root/m.name).resolve();assert p.is_relative_to(root.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
assert hashlib.sha256((root/'vectors_protocol.json').read_bytes()).hexdigest()=='PROTO'
with (root/'vectors.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-u','-B',str(root/'board_vectors.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
record={'PID':child.pid,'expected_actual_vectors':132,'warmups':2,'PL_actions':0}
(root/'vectors_launch.json').write_text(json.dumps(record,indent=2)+'\\n');print(json.dumps(record))
PY
'''.replace('DIGEST',meta['sha256']).replace('MEMBERS',str(meta['members'])).replace('PROTO',meta['protocol_sha256'])
(ROOT/'tools/launch_vectors.sh').write_text(script,newline='\n');print(json.dumps(meta))
