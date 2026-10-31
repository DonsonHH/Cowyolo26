from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,ast,tarfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
old=ROOT/'tools/board_video.py';text=old.read_text()
oldhelper='def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()'
assert text.count(oldhelper)==1
text=text.replace(oldhelper,'def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()')
text=text.replace("ROOT/'board_protocol.json'","ROOT/'board_protocol_v2.json'").replace("out=ROOT/'results'","out=ROOT/'results_v2'")
text=text.replace(" try:\n  for row in p['payload_files']:"," try:\n  progress('before_payload_validation',None)\n  for row in p['payload_files']:")
file=ROOT/'tools/board_video_v2.py';assert not file.exists();file.write_text(text,newline='\n')
tree=ast.parse(text);helper=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='sha')
context={'Path':Path,'hashlib':hashlib};exec(compile(ast.Module(body=[helper],type_ignores=[]),'<helper_regression>','exec'),context)
assert context['sha'](str(old))==context['sha'](old)==sha(old)
p=json.loads((ROOT/'protocol/board_video_v1.json').read_text());p.update({'status':'FROZEN_PATH_HELPER_REPAIR_BEFORE_V2_BOARD_FORWARDS',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'failed_previous_PID':25957,'failed_output_directory_preserved':'results',
 'repair':'Path(p) in hashing helper; PL.bitfile_name is str; write progress before validation; no model/input/timing/association changes.',
 'failed_script_unconditional_string_path_hash_precedes_graph_constructor_and_all_forwards':True,
 'new_script_sha256':sha(file),'previous_protocol_sha256':sha(ROOT/'protocol/board_video_v1.json')})
p['payload_files'].append({'file':'board_video_v2.py','bytes':file.stat().st_size,'sha256':sha(file)})
protocol=ROOT/'protocol/board_video_v2.json';assert not protocol.exists();protocol.write_text(json.dumps(p,indent=2)+'\n')
archive=ROOT/'board_video_v2_patch.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for source,name in [(file,'board_video_v2.py'),(protocol,'board_protocol_v2.json')]:tar.add(source,arcname=name,recursive=False)
record={'bytes':archive.stat().st_size,'sha256':sha(archive),'members':2,'protocol_sha256':sha(protocol),'helper_string_and_Path_regression_passed':True}
(ROOT/'evidence/board_v2_patch.json').write_text(json.dumps(record,indent=2)+'\n')
launch='''set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import os,sys,json,hashlib,tarfile,subprocess,fcntl
from pynq import PL
root=Path('/home/xilinx/jupyter_notebooks/cow_research_rot192_video_20261029')
old=json.loads((root/'launch.json').read_text());assert old['PID']==25957 and not (Path('/proc')/str(old['PID'])).exists()
assert not (root/'results/record.json').exists() and not (root/'results/terminal.json').exists()
assert isinstance(PL.bitfile_name,str)
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
observed={'old_PID':old['PID'],'old_PID_absent':True,'PL_bitfile_type':type(PL.bitfile_name).__name__,'PL_bit_sha256':hashlib.sha256(Path(PL.bitfile_name).read_bytes()).hexdigest(),
 'old_results_files':sorted(p.name for p in (root/'results').iterdir()),'first_failed_script_forwards':0,
 'zero_forward_evidence':'Unconditional sha(PL.bitfile_name str) occurs before lock, NativeGraph construction and all run calls; process is absent and log finally repeats same helper error.'}
assert observed['PL_bit_sha256']=='5da7a73bf52fd5153e25de5c28a40e2080c29e960d767008e0e804ec527bbfd8'
(root/'failed_v1_forensic.json').write_text(json.dumps(observed,indent=2)+'\\n')
archive=root/'v2_patch.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
assert not (root/'launch_v2.json').exists() and not (root/'results_v2').exists()
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['board_video_v2.py','board_protocol_v2.json']
  p=root/m.name;assert not p.exists();p.write_bytes(tar.extractfile(m).read())
assert hashlib.sha256((root/'board_protocol_v2.json').read_bytes()).hexdigest()=='PROTO'
with (root/'run_v2.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-u','-B',str(root/'board_video_v2.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
record={'PID':child.pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'actual_video_model_forwards_expected':2654,'warmups':2,'counter_paths_expected':6,'old_failed_PID':25957}
(root/'launch_v2.json').write_text(json.dumps(record,indent=2)+'\\n');print(json.dumps({'preflight':observed,'launch':record}))
PY
'''.replace('DIGEST',record['sha256']).replace('PROTO',record['protocol_sha256'])
(ROOT/'tools/launch_board_v2.sh').write_text(launch,newline='\n')
status=(ROOT/'tools/board_status.sh').read_text().replace("root/'launch.json'","root/'launch_v2.json'").replace('results/','results_v2/').replace("root/'run.log'","root/'run_v2.log'")
(ROOT/'tools/board_status_v2.sh').write_text(status,newline='\n');print(json.dumps(record))
