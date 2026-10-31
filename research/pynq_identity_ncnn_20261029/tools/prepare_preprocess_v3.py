from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,ast,tarfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
actual=json.loads(json.loads((ROOT/'evidence/board_Pillow_sources_and_diag_progress.json').read_text())['stdout'])
reference=json.loads((ROOT/'evidence/server_Pillow_sources.json').read_text())
assert 'new_height = int(' in actual['contain_source'] and 'new_height = round(' in reference['contain_source']
assert 'x = int(' in actual['pad_source'] and 'x = round(' in reference['pad_source']
source=ROOT/'tools/ncnn_encoder_v2.py';text=source.read_text()
marker="    image=ImageOps.pad(image.convert('RGB'),(224,224),method=getattr(Image,'Resampling',Image).BILINEAR,color=(127,127,127),centering=(.5,.5))"
assert text.count(marker)==1
replacement='''    # Match the frozen Pillow11.3 training transform geometry on Pillow9.0.1.
    # Pillow9 ImageOps.contain/pad truncate; Pillow11 rounds both resize and offset.
    image=image.convert('RGB');size=(224,224)
    ratio=image.width/image.height
    target=(224,round(image.height/image.width*224)) if ratio>1 else (round(image.width/image.height*224),224) if ratio<1 else size
    resized=image.resize(target,resample=getattr(Image,'Resampling',Image).BILINEAR)
    if resized.size==size:image=resized
    else:
        image=Image.new('RGB',size,(127,127,127))
        position=(round((224-resized.width)*.5),0) if resized.width!=224 else (0,round((224-resized.height)*.5))
        image.paste(resized,position)'''
text=text.replace(marker,replacement)
file=ROOT/'tools/ncnn_encoder_v3.py';assert not file.exists();file.write_text(text,newline='\n');ast.parse(text)
script=(ROOT/'tools/board_vectors_v2.py').read_text().replace('ncnn_encoder_v2','ncnn_encoder_v3').replace('vectors_protocol_v2.json','vectors_protocol_v3.json').replace('vectors_results_v2','vectors_results_v3')
marker="  vectors=load(ROOT/'vector_manifest.json');encoder=Encoder(ROOT,threads=1)";assert marker in script
replacement='''  vectors=load(ROOT/'vector_manifest.json')
  preprocess_gate=[]
  for row in vectors:
   with np.load(ROOT/row['file']) as a:expected=a['input']
   with Image.open(ROOT/row['image_file']) as image:observed=body_tensor(image)
   error=float(np.max(np.abs(expected-observed)))
   preprocess_gate.append({'name':row['name'],'maximum_tensor_difference':error,'passes':error<=p['Pillow_preprocessing_max_absolute_tolerance']})
  write(out/'preprocessing_gate.json',{'status':'CHECKED_BEFORE_ANY_NATIVE_CREATE_OR_NETWORK_FORWARD','cases':preprocess_gate,'model_forwards':0})
  assert all(r['passes'] for r in preprocess_gate),'Preprocessing132imagegatefailedbeforemodelcreate'
  encoder=Encoder(ROOT,threads=1)'''
script=script.replace(marker,replacement)
runner=ROOT/'tools/board_vectors_v3.py';runner.write_text(script,newline='\n');ast.parse(script)
p=json.loads((ROOT/'protocol/board_vectors_v2.json').read_text());p.update({'status':'FROZEN_EXACT_PILLOW11_GEOMETRY_REPAIR_BEFORE_VECTOR_V3',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'failed_v2_PID':1634,'failed_v2_model_forwards':4,'failed_v2_warmups':2,
 'preprocessing_repair':'Explicit round-on-resize and round-on-centering matches frozenPillow11geometry without replacing globalPillow9.',
 'numeric_or_retrieval_gate_relaxed':False,'all132_preprocessing_gate_before_any_model_forward':True,
 'server_Pillow_source_evidence_sha256':sha(ROOT/'evidence/server_Pillow_sources.json'),
 'board_Pillow_source_evidence_sha256':sha(ROOT/'evidence/board_Pillow_sources_and_diag_progress.json')})
p['files']=[r for r in p['files'] if r['file'] not in ['ncnn_encoder_v2.py','board_vectors_v2.py']]
p['files'].extend([{'file':x.name,'sha256':sha(x),'bytes':x.stat().st_size} for x in [file,runner]])
protocol=ROOT/'protocol/board_vectors_v3.json';protocol.write_text(json.dumps(p,indent=2)+'\n')
archive=ROOT/'board_vectors_v3_patch.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for source,name in [(file,file.name),(runner,runner.name),(protocol,'vectors_protocol_v3.json')]:tar.add(source,arcname=name,recursive=False)
meta={'sha256':sha(archive),'bytes':archive.stat().st_size,'members':3,'protocol_sha256':sha(protocol)}
(ROOT/'evidence/board_vectors_v3_patch.json').write_text(json.dumps(meta,indent=2)+'\n')
launch='''set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess,sys,os
root=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029')
t=json.loads((root/'vectors_results_v2/terminal.json').read_text());assert t['status']=='FAILED' and t['model_forwards']==4 and not (Path('/proc')/str(t['PID'])).exists()
assert not (root/'vectors_results_v3').exists() and not (root/'vectors_v3_launch.json').exists()
archive=root/'vectors_v3_patch.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['ncnn_encoder_v3.py','board_vectors_v3.py','vectors_protocol_v3.json']
  path=root/m.name;assert not path.exists();path.write_bytes(tar.extractfile(m).read())
with (root/'vectors_v3.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_vectors_v3.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'expected_vectors':132,'warmups':2,'all132_photo_inputs_prechecked_before_model':True,'prior_failed_results_retained':True}
(root/'vectors_v3_launch.json').write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r))
PY
'''.replace('DIGEST',meta['sha256'])
(ROOT/'tools/launch_vectors_v3.sh').write_text(launch,newline='\n')
status=(ROOT/'tools/vectors_status_v2.sh').read_text().replace('vectors_v2_launch','vectors_v3_launch').replace('vectors_results_v2','vectors_results_v3').replace('vectors_v2.log','vectors_v3.log')
(ROOT/'tools/vectors_status_v3.sh').write_text(status,newline='\n');print(json.dumps(meta))
