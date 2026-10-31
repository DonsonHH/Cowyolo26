from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,ast,tarfile
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
text=(PROJECT/'pynq_rot192_compile_20261029/tools/board_cow_vectors.py').read_text().replace('192','320')
text=text.replace("ROOT/'protocol.json'","ROOT/'protocol_v2.json'").replace("out=ROOT/'results'","out=ROOT/'results_v2'")
assert 'sha320' not in text and 'hashlib.sha256' in text and "p['size']==320" in text and 'NativeGraph(320,' in text
tree=ast.parse(text);helper=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='sha')
ns={'Path':Path,'hashlib':hashlib};exec(compile(ast.Module(body=[helper],type_ignores=[]),'<SHA256_path_regression>','exec'),ns)
assert ns['sha'](str(ROOT/'protocol/board_s320_v1.json'))==sha(ROOT/'protocol/board_s320_v1.json')
file=ROOT/'tools/board_s320_vectors_v2.py';file.write_text(text,newline='\n')
p=json.loads((ROOT/'protocol/board_s320_v1.json').read_text());p.update({'status':'FROZEN_S320_DIMENSION_REPLACEMENT_REPAIR_BEFORE_MODEL_FORWARD','created_UTC':datetime.now(timezone.utc).isoformat(),
 'failed_first_board_PID':10019,'old_failed_script_preserved':True,'old_failed_network_forwards':0,
 'repair':'Generatefrom192original,modifyonly192->320dimensionstrings;leaveSHA256algorithmandprotocolkeysintact;results_v2.',
 'all_data_model_reference_and_gate_values_unchanged':True})
p['payload_files'].append({'file':file.name,'bytes':file.stat().st_size,'sha256':sha(file)})
proto=ROOT/'protocol/board_s320_v2.json';proto.write_text(json.dumps(p,indent=2)+'\n')
archive=ROOT/'s320_repair_patch.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for source,name in [(file,file.name),(proto,'protocol_v2.json')]:tar.add(source,arcname=name,recursive=False)
meta={'sha256':sha(archive),'bytes':archive.stat().st_size,'members':2,'protocol_sha256':sha(proto),'hash_helper_string_and_Path_test_passed':True}
(ROOT/'evidence/s320_repair_patch.json').write_text(json.dumps(meta,indent=2)+'\n')
launch='''set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OPENBLAS_NUM_THREADS=2
export OMP_NUM_THREADS=2
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,tarfile,hashlib,subprocess,sys,os
root=Path('/home/xilinx/jupyter_notebooks/cow_research_o8_s320_qual_20261030')
old=json.loads((root/'launch.json').read_text());assert old['PID']==10019 and not Path('/proc/10019').exists()
assert not list((root/'results').iterdir()) and not (root/'results_v2').exists()
archive=root/'repair_patch.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['board_s320_vectors_v2.py','protocol_v2.json']
  p=root/m.name;assert not p.exists();p.write_bytes(tar.extractfile(m).read())
with (root/'run_v2.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_s320_vectors_v2.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'size':320,'expected_model_forwards':10,'legacy_numpy_reference_failure_preserved':True,'ordered_reference_qualified':True}
(root/'launch_v2.json').write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r))
PY
'''.replace('DIGEST',meta['sha256'])
(ROOT/'tools/launch_s320_v2.sh').write_text(launch,newline='\n')
status=(ROOT/'tools/s320_status_board_vectors.sh').read_text().replace("root/'launch.json'","root/'launch_v2.json'").replace('results/','results_v2/').replace("root/'run.log'","root/'run_v2.log'")
(ROOT/'tools/s320_status_v2.sh').write_text(status,newline='\n')
collect=(ROOT/'tools/s320_collect_board_vectors.sh').read_text().replace("root/'results/","root/'results_v2/").replace("root/'results'","root/'results_v2'").replace('protocol.json','protocol_v2.json').replace('board_s320_vectors.py','board_s320_vectors_v2.py').replace('launch.json','launch_v2.json').replace('run.log','run_v2.log')
collect=collect.replace("files.extend([root/'protocol_v2.json'", "files.extend([root/'protocol.json',root/'board_s320_vectors.py',root/'launch.json',root/'run.log',root/'protocol_v2.json'")
(ROOT/'tools/s320_collect_v2.sh').write_text(collect,newline='\n');print(json.dumps(meta))
