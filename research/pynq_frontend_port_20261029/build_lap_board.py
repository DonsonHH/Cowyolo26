from pathlib import Path
from datetime import datetime,timezone
import os,sys,json,hashlib,tarfile,subprocess,time
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):
 path=ROOT/name;assert not path.exists();path.write_text(json.dumps(value,indent=2)+'\n')
try:
 import numpy,Cython,setuptools
 source=ROOT/'lap-0.5.13.tar.gz';assert sha(source)=='9eff7169e3ca452995af0493cc20d35452c4bfd06122c36c06457119ffbd411b'
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
