from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,copy
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((ROOT/'regression_v1.json').read_text());files={}
remote='/share/home/renly/projects/idcoo_research_20261026/'
for row in p['caches']:
 for kind in ['raw','trace']:
  relative=row[kind+'_file'].removeprefix(remote)
  assert relative!=row[kind+'_file']
  first,*rest=Path(relative).parts;local=PROJECT/first/'delivery'/Path(*rest)
  assert sha(local)==row[kind+'_sha256']
  packet='cached/'+relative;files[packet]=local;row[kind+'_file']=packet
for row in p['files']:files[row['file']]=ROOT/row['file']
files['board_regression.py']=ROOT/'board_regression.py'
p.update({'status':'FROZEN_BEFORE_ACTUAL_ARM_TRACKER_REGRESSION','created_UTC':datetime.now(timezone.utc).isoformat(),
 'board_normalized_axis_tolerance':2e-6,'board_LAP_source_sha256':'9eff7169e3ca452995af0493cc20d35452c4bfd06122c36c06457119ffbd411b',
 'board_global_numpy_unchanged':'1.21.5; task-specific native extension; upstream LAP dependency minimum1.21.6 not certified globally',
 'files':[{'file':name,'sha256':sha(local),'bytes':local.stat().st_size} for name,local in sorted(files.items())]})
proto=ROOT/'board_regression_v1.json';assert not proto.exists();proto.write_text(json.dumps(p,indent=2)+'\n');files['board_regression_v1.json']=proto
archive=ROOT/'board_regression_payload.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for name,local in sorted(files.items()):tar.add(local,arcname=name,recursive=False)
meta={'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files),'protocol_sha256':sha(proto)}
(ROOT/'board_regression_transfer.json').write_text(json.dumps(meta,indent=2)+'\n')
script='''set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import tarfile,json,hashlib,subprocess,sys,os
root=Path('/home/xilinx/jupyter_notebooks/cow_research_numpy_tracker_20261029')
terminal=json.loads((root/'build_terminal.json').read_text());assert terminal['success'] and not (Path('/proc')/str(terminal['PID'])).exists()
assert not (root/'regression_launch.json').exists()
archive=root/'regression_payload.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
with tarfile.open(archive) as tar:
 assert len(tar.getmembers())==MEMBERS
 for member in tar.getmembers():
  assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
  file=(root/member.name).resolve();assert file.is_relative_to(root.resolve()) and not file.exists()
  file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(tar.extractfile(member).read())
assert hashlib.sha256((root/'board_regression_v1.json').read_bytes()).hexdigest()=='PROTO'
with (root/'regression.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-u','-B',str(root/'board_regression.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
result={'PID':child.pid,'expected_traces':90,'expected_observations':82020,'network_or_PL_actions':0}
(root/'regression_launch.json').write_text(json.dumps(result,indent=2)+'\\n');print(json.dumps(result))
PY
'''.replace('DIGEST',meta['sha256']).replace('MEMBERS',str(meta['members'])).replace('PROTO',meta['protocol_sha256'])
(ROOT/'launch_regression.sh').write_text(script,newline='\n');print(json.dumps(meta))
