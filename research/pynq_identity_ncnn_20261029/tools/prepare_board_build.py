from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=load(ROOT/'evidence/source_staging.json');source=next(r for r in source['artifacts'] if r['package']=='ncnn_source')
q=ROOT/'delivery/results/export_v2';s=load(q/'summary.json');assert s['all_retrieval_decisions_exact'] and s['real_image_forwards']=={'TorchCPU':132,'ncnnCPU':132}
layers=load(ROOT/'evidence/layer_inventory.json')
required=set(s['ncnn_operators'])|{'ReLU','Clip','Sigmoid','Mish','Padding','Flatten','Packing','Cast'}
assert required<=set(layers)
options=['-DCMAKE_BUILD_TYPE=Release','-DNCNN_VERSION=20261020','-DNCNN_SHARED_LIB=OFF','-DCMAKE_POSITION_INDEPENDENT_CODE=ON',
 '-DNCNN_OPENMP=ON','-DNCNN_THREADS=ON','-DNCNN_VULKAN=OFF','-DNCNN_RUNTIME_CPU=OFF','-DNCNN_ARM82=OFF','-DNCNN_ARM82DOT=OFF',
 '-DNCNN_INT8=OFF','-DNCNN_WEIGHT_QUANT=OFF','-DNCNN_BF16=OFF','-DNCNN_BUILD_TESTS=OFF','-DNCNN_BUILD_BENCHMARK=OFF',
 '-DNCNN_BUILD_EXAMPLES=OFF','-DNCNN_BUILD_TOOLS=OFF','-DNCNN_PYTHON=OFF','-DNCNN_PIXEL=OFF','-DNCNN_PIXEL_ROTATE=OFF',
 '-DNCNN_PIXEL_AFFINE=OFF','-DNCNN_PIXEL_DRAWING=OFF','-DCMAKE_C_FLAGS=-mcpu=cortex-a9 -mfpu=neon -mfloat-abi=hard',
 '-DCMAKE_CXX_FLAGS=-mcpu=cortex-a9 -mfpu=neon -mfloat-abi=hard']
options += ['-DWITH_LAYER_'+name.lower()+'='+('ON' if name in required else 'OFF') for name in layers]
proto={'status':'FROZEN_BEFORE_ISOLATED_ARM_NCNN_BUILD','created_UTC':datetime.now(timezone.utc).isoformat(),'source_sha256':source['sha256'],
 'source_tag':'20261020','required_layers':sorted(required),'CMake_options':options,'build_parallelism':1,
 'encoder_checkpoint_sha256':s['encoder_checkpoint_sha256'],'param_sha256':sha(q/'encoder.ncnn.param'),'weights_sha256':sha(q/'encoder.ncnn.bin'),
 'bridge_sha256':sha(ROOT/'tools/encoder_bridge.cpp'),'numerical_gate_protocol_sha256':sha(ROOT/'protocol/encoder_v1.json'),
 'global_package_or_toolchain_changes':False,'PL_programming_or_inference_during_build':False,'whole_goal_complete':False}
protocol=ROOT/'protocol/board_build_v1.json';assert not protocol.exists();protocol.write_text(json.dumps(proto,indent=2)+'\n')
files={'ncnn_source.tar.gz':ROOT/'sources'/source['file'],'encoder.ncnn.param':q/'encoder.ncnn.param','encoder.ncnn.bin':q/'encoder.ncnn.bin',
 'encoder_bridge.cpp':ROOT/'tools/encoder_bridge.cpp','build_protocol.json':protocol}
build='''from pathlib import Path
import os,sys,hashlib,json,tarfile,subprocess,time,traceback
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,x):
 p=ROOT/name;assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\\n')
start=time.perf_counter_ns()
try:
 p=json.loads((ROOT/'build_protocol.json').read_text())
 for key,file in [('source_sha256','ncnn_source.tar.gz'),('param_sha256','encoder.ncnn.param'),('weights_sha256','encoder.ncnn.bin'),('bridge_sha256','encoder_bridge.cpp')]:assert sha(ROOT/file)==p[key]
 assert os.uname().machine=='armv7l'
 source=ROOT/'source';source.mkdir(exist_ok=False)
 with tarfile.open(ROOT/'ncnn_source.tar.gz') as tar:
  for member in tar.getmembers():
   assert not member.name.startswith('/') and '..' not in Path(member.name).parts and (member.isfile() or member.isdir())
   path=(source/member.name).resolve();assert path.is_relative_to(source.resolve())
   if member.isdir():path.mkdir(parents=True,exist_ok=True);continue
   path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(member).read())
 build=ROOT/'build';sdk=ROOT/'install'
 configure=['cmake','-S',str(source/'ncnn-20261020'),'-B',str(build),'-DCMAKE_INSTALL_PREFIX='+str(sdk),*p['CMake_options']]
 commands=[configure,['cmake','--build',str(build),'--parallel','1'],['cmake','--install',str(build)],
 ['g++','-O3','-std=c++11','-shared','-fPIC','-fopenmp','-mcpu=cortex-a9','-mfpu=neon','-mfloat-abi=hard',
  '-I'+str(sdk/'include/ncnn'),str(ROOT/'encoder_bridge.cpp'),str(sdk/'lib/libncnn.a'),'-o',str(ROOT/'libcow_encoder.so'),'-lpthread','-ldl']]
 for i,command in enumerate(commands):
  save('stage_'+str(i)+'.json',{'command':command,'monotonic_ns':time.monotonic_ns()})
  with (ROOT/('stage_'+str(i)+'.log')).open('xb') as log:completed=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
  assert completed.returncode==0,('Buildstagefailed',i)
 result={'status':'ISOLATED_ARMV7_NEON_NCNN_AND_C_ABI_BRIDGE_BUILD_COMPLETE','PID':os.getpid(),'source_sha256':p['source_sha256'],
  'encoder_checkpoint_sha256':p['encoder_checkpoint_sha256'],'bridge_library_sha256':sha(ROOT/'libcow_encoder.so'),
  'bridge_library_bytes':(ROOT/'libcow_encoder.so').stat().st_size,'wall_s':(time.perf_counter_ns()-start)/1e9,'inference_still_required':True,
  'global_dependency_changes':False,'model_or_PL_actions':0}
 save('build_result.json',result);print(json.dumps(result),flush=True)
except BaseException as e:
 save('build_failure.json',{'error':repr(e),'traceback':traceback.format_exc()});raise
finally:
 save('build_terminal.json',{'PID':os.getpid(),'success':(ROOT/'build_result.json').exists(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()})
'''
file=ROOT/'tools/build_ncnn_board.py';assert not file.exists();file.write_text(build,newline='\n');files['build_ncnn_board.py']=file
archive=ROOT/'board_build_payload.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for name,file in files.items():tar.add(file,arcname=name,recursive=False)
meta={'sha256':sha(archive),'bytes':archive.stat().st_size,'members':len(files),'protocol_sha256':sha(protocol)}
(ROOT/'evidence/board_build_payload.json').write_text(json.dumps(meta,indent=2)+'\n')
target='/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029'
create='''set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json
root=Path('TARGET');root.mkdir(exist_ok=False);print(json.dumps({'status':'ISOLATED_NCNN_BUILD_DIRECTORY_CREATED','path':str(root)}))
PY
'''.replace('TARGET',target)
(ROOT/'tools/create_board_task.sh').write_text(create,newline='\n')
launch='''set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import tarfile,json,hashlib,subprocess,sys,os
root=Path('TARGET');archive=root/'build_payload.tar.gz'
video=Path('/home/xilinx/jupyter_notebooks/cow_research_rot192_video_20261029')
t=json.loads((video/'results_v2/terminal.json').read_text());assert t['status']=='ALL2654_ACTUAL_O8_VIDEO_INPUTS_AND_REAL_ARM_COUNTER_PATHS_COMPLETE' and not (Path('/proc')/str(t['PID'])).exists()
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
assert not (root/'launch.json').exists()
with tarfile.open(archive) as tar:
 assert len(tar.getmembers())==MEMBERS
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(root/m.name).resolve();assert p.is_relative_to(root.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
with (root/'run.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-u','-B',str(root/'build_ncnn_board.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
record={'PID':child.pid,'build_parallelism':1,'global_dependency_changes':False,'model_or_PL_actions':0,'prior_foreground_replay_terminated':True}
(root/'launch.json').write_text(json.dumps(record,indent=2)+'\\n');print(json.dumps(record))
PY
'''.replace('TARGET',target).replace('DIGEST',meta['sha256']).replace('MEMBERS',str(meta['members']))
(ROOT/'tools/launch_board_build.sh').write_text(launch,newline='\n');print(json.dumps(meta))
