from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,tarfile,ast
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
loader=(ROOT/'tools/ncnn_encoder.py').read_text();assert "root/'libcow_encoder.so'" in loader
loader=loader.replace("root/'libcow_encoder.so'","root/'libcow_encoder_v2.so'")
file=ROOT/'tools/ncnn_encoder_v2.py';assert not file.exists();file.write_text(loader,newline='\n');ast.parse(loader)
text=(ROOT/'tools/board_vectors.py').read_text().replace('from ncnn_encoder import','from ncnn_encoder_v2 import')
text=text.replace('vectors_protocol.json','vectors_protocol_v2.json').replace("out=ROOT/'vectors_results'","out=ROOT/'vectors_results_v2'")
text=text.replace("ROOT/'build_result.json'","ROOT/'build_v2_result.json'").replace("ROOT/'build_terminal.json'","ROOT/'build_v2_terminal.json'").replace("ROOT/'libcow_encoder.so'","ROOT/'libcow_encoder_v2.so'")
script=ROOT/'tools/board_vectors_v2.py';assert not script.exists();script.write_text(text,newline='\n');ast.parse(text)
p=json.loads((ROOT/'protocol/board_vectors_v1.json').read_text());p.update({'status':'FROZEN_A9_INSTRUCTION_COMPATIBLE_VECTOR_RETRY','created_UTC':datetime.now(timezone.utc).isoformat(),
 'failed_first_PID':31016,'failed_original_files_preserved':True,'same_input_images_tensor_vectors_numeric_and_retrieval_gates':True,
 'new_loader_sha256':sha(file),'new_vector_runner_sha256':sha(script),'native_build_v2_protocol_sha256':sha(ROOT/'protocol/board_build_v2.json')})
p['files']=[r for r in p['files'] if r['file'] not in ['ncnn_encoder.py','board_vectors.py']]
p['files'].extend([{'file':q.name,'sha256':sha(q),'bytes':q.stat().st_size} for q in [file,script]])
proto=ROOT/'protocol/board_vectors_v2.json';proto.write_text(json.dumps(p,indent=2)+'\n')
archive=ROOT/'board_vectors_v2_patch.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for source,name in [(file,file.name),(script,script.name),(proto,'vectors_protocol_v2.json')]:tar.add(source,arcname=name,recursive=False)
meta={'bytes':archive.stat().st_size,'sha256':sha(archive),'members':3,'protocol_sha256':sha(proto)}
(ROOT/'evidence/board_vectors_v2_patch.json').write_text(json.dumps(meta,indent=2)+'\n')
launch='''set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,tarfile,hashlib,subprocess,sys,os
root=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029')
t=json.loads((root/'build_v2_terminal.json').read_text());assert t['success'] and not (Path('/proc')/str(t['PID'])).exists()
assert not Path('/proc/31016').exists() and not (root/'vectors_results_v2').exists()
attributes=subprocess.check_output(['readelf','-A',str(root/'libcow_encoder_v2.so')],text=True);assert 'VFPv4' not in attributes and 'Fused-MAC' not in attributes
(root/'A9_library_attributes_v2.txt').write_text(attributes)
archive=root/'vectors_v2_patch.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['ncnn_encoder_v2.py','board_vectors_v2.py','vectors_protocol_v2.json']
  path=root/m.name;assert not path.exists();path.write_bytes(tar.extractfile(m).read())
with (root/'vectors_v2.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_vectors_v2.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
record={'PID':child.pid,'expected_actual_vectors':132,'warmups':2,'PL_actions':0,'old_failed_PID':31016,'VFPv4_present_in_v2_binary':False}
(root/'vectors_v2_launch.json').write_text(json.dumps(record,indent=2)+'\\n');print(json.dumps(record))
PY
'''.replace('DIGEST',meta['sha256'])
(ROOT/'tools/launch_vectors_v2.sh').write_text(launch,newline='\n')
status=(ROOT/'tools/vectors_status.sh').read_text().replace('vectors_launch.json','vectors_v2_launch.json').replace('vectors_results/','vectors_results_v2/').replace('vectors.log','vectors_v2.log')
(ROOT/'tools/vectors_status_v2.sh').write_text(status,newline='\n');print(json.dumps(meta))
