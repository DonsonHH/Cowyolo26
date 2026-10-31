from pathlib import Path
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent
meta=json.loads((ROOT/'lap_source_provenance.json').read_text())
target='/home/xilinx/jupyter_notebooks/cow_research_numpy_tracker_20261029'
build='''from pathlib import Path
from datetime import datetime,timezone
import os,sys,json,hashlib,tarfile,subprocess,time
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):
 path=ROOT/name;assert not path.exists();path.write_text(json.dumps(value,indent=2)+'\\n')
try:
 import numpy,Cython,setuptools
 source=ROOT/'lap-0.5.13.tar.gz';assert sha(source)=='DIGEST'
 out=ROOT/'source';out.mkdir(exist_ok=False)
 with tarfile.open(source) as tar:
  for m in tar.getmembers():
   assert not m.name.startswith('/') and '..' not in Path(m.name).parts and (m.isfile() or m.isdir())
   path=(out/m.name).resolve();assert path.is_relative_to(out.resolve())
   if m.isdir():path.mkdir(parents=True,exist_ok=True);continue
   path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(m).read())
 package=out/'lap-0.5.13'
 save('build_environment.json',{'numpy':numpy.__version__,'Cython':Cython.__version__,'setuptools':setuptools.__version__,
  'python':sys.version,'machine':os.uname().machine,'source_sha256':sha(source),
  'declared_numpy_minimum':'1.21.6','existing_board_numpy':'1.21.5','global_dependency_changes':False,
  'compatibility_status':'PENDING_TASK_SPECIFIC_REGRESSION; direct native extension build with existing board headers'})
 with (ROOT/'compile.log').open('xb') as log:
  result=subprocess.run([sys.executable,'setup.py','build_ext','--inplace'],cwd=package,stdout=log,stderr=subprocess.STDOUT)
 assert result.returncode==0,'NativeLAPbuildfailed;preservelogs'
 sys.path.insert(0,str(package));import lap,numpy as np
 assert lap.__version__=='0.5.13'
 costs=np.asarray([[.1,.9],[.8,.2]],dtype=np.float64)
 value,x,y=lap.lapjv(costs,extend_cost=True,cost_limit=.8)
 assert x.tolist()==y.tolist()==[0,1] and abs(value-.3)<1e-12
 result={'status':'ISOLATED_LAP_NATIVE_EXTENSION_BUILT_SMOKE_ONLY','PID':os.getpid(),'lap_version':lap.__version__,
  'lap_file':lap.__file__,'extension_files':[{'path':str(p),'sha256':sha(p)} for p in package.rglob('*.so')],
  'smoke_cost':value,'global_numpy_replaced':False,'tracker_regression_still_required':True,'model_or_PL_actions':0}
 save('build_result.json',result)
except BaseException as e:
 import traceback
 save('build_failure.json',{'error':repr(e),'traceback':traceback.format_exc()})
 raise
finally:
 save('build_terminal.json',{'PID':os.getpid(),'success':(ROOT/'build_result.json').exists(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()})
'''.replace('DIGEST',meta['sha256'])
(ROOT/'build_lap_board.py').write_text(build,newline='\n')
create='''set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json
root=Path('TARGET');root.mkdir(exist_ok=False)
print(json.dumps({'status':'ISOLATED_NUMPY_TRACKER_BUILD_DIRECTORY_CREATED','path':str(root),'model_or_PL_actions':0}))
PY
'''.replace('TARGET',target)
(ROOT/'create_board_task.sh').write_text(create,newline='\n')
launch='''set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import os,sys,json,hashlib,subprocess
root=Path('TARGET');assert not (root/'launch.json').exists()
assert hashlib.sha256((root/'build_lap_board.py').read_bytes()).hexdigest()=='SCRIPT'
assert hashlib.sha256((root/'lap-0.5.13.tar.gz').read_bytes()).hexdigest()=='DIGEST'
with (root/'run.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-u','-B',str(root/'build_lap_board.py')],stdout=log,stderr=subprocess.STDOUT,cwd=root,env=os.environ.copy(),start_new_session=True)
result={'PID':child.pid,'task':'Isolated LAP0.5.13 source build','model_or_PL_actions':0}
(root/'launch.json').write_text(json.dumps(result,indent=2)+'\\n');print(json.dumps(result))
PY
'''.replace('TARGET',target).replace('DIGEST',meta['sha256']).replace('SCRIPT',hashlib.sha256((ROOT/'build_lap_board.py').read_bytes()).hexdigest())
(ROOT/'launch_build.sh').write_text(launch,newline='\n')
print(json.dumps({'board_task':target,'source_bytes':meta['bytes'],'global_dependency_changes':False}))
