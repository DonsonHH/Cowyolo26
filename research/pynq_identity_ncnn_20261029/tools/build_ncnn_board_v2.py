from pathlib import Path
import os,sys,hashlib,json,tarfile,subprocess,time,traceback
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,x):
 p=ROOT/name;assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n')
start=time.perf_counter_ns()
try:
 p=json.loads((ROOT/'build_protocol_v2.json').read_text())
 for key,file in [('source_sha256','ncnn_source.tar.gz'),('param_sha256','encoder.ncnn.param'),('weights_sha256','encoder.ncnn.bin'),('bridge_sha256','encoder_bridge.cpp')]:assert sha(ROOT/file)==p[key]
 assert os.uname().machine=='armv7l'
 source=ROOT/'source';assert source.is_dir()
 build=ROOT/'build_v2';sdk=ROOT/'install_v2'
 configure=['cmake','-S',str(source/'ncnn-20261020'),'-B',str(build),'-DCMAKE_INSTALL_PREFIX='+str(sdk),*p['CMake_options']]
 commands=[configure,['cmake','--build',str(build),'--parallel','1'],['cmake','--install',str(build)],
 ['g++','-O3','-std=c++11','-shared','-fPIC','-fopenmp','-mcpu=cortex-a9','-mfpu=neon','-mfloat-abi=hard',
  '-I'+str(sdk/'include/ncnn'),str(ROOT/'encoder_bridge.cpp'),str(sdk/'lib/libncnn.a'),'-o',str(ROOT/'libcow_encoder_v2.so'),'-lpthread','-ldl']]
 for i,command in enumerate(commands):
  save('v2_stage_'+str(i)+'.json',{'command':command,'monotonic_ns':time.monotonic_ns()})
  with (ROOT/('v2_stage_'+str(i)+'.log')).open('xb') as log:completed=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT)
  assert completed.returncode==0,('Buildstagefailed',i)
 result={'status':'ISOLATED_ARMV7_NEON_NCNN_AND_C_ABI_BRIDGE_BUILD_COMPLETE','PID':os.getpid(),'source_sha256':p['source_sha256'],
  'encoder_checkpoint_sha256':p['encoder_checkpoint_sha256'],'bridge_library_sha256':sha(ROOT/'libcow_encoder_v2.so'),
  'bridge_library_bytes':(ROOT/'libcow_encoder_v2.so').stat().st_size,'wall_s':(time.perf_counter_ns()-start)/1e9,'inference_still_required':True,
  'global_dependency_changes':False,'model_or_PL_actions':0}
 save('build_v2_result.json',result);print(json.dumps(result),flush=True)
except BaseException as e:
 save('build_v2_failure.json',{'error':repr(e),'traceback':traceback.format_exc()});raise
finally:
 save('build_v2_terminal.json',{'PID':os.getpid(),'success':(ROOT/'build_v2_result.json').exists(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()})
