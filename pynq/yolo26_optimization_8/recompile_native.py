"""Freeze native sources and rebuild independently; never replaces active library."""
import pathlib,argparse,subprocess,json,hashlib,shutil,platform
D=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--compiler',default='g++');a=p.parse_args();O=a.output.resolve();O.mkdir(parents=True,exist_ok=False)
files=['queue_runtime.cpp','native_runtime.cpp','graph_executor.cpp','resident_methods.inc','software_fusion.inc'];hashes={}
for name in files:shutil.copy2(D/'native_sources'/name,O/name);hashes[name]=hashlib.sha256((O/name).read_bytes()).hexdigest()
arm=platform.machine().startswith(('arm','ARM'));library='native_queue.so' if arm else 'native_queue_pc.dll';cmd=[a.compiler,'-O3','-std=c++17','-shared','-fopenmp','-ffp-contract=off']
if arm:cmd+=['-fPIC','-mcpu=cortex-a9','-mfpu=neon','-mfloat-abi=hard']
elif platform.system()=='Windows':cmd+=['-static-libgcc','-static-libstdc++']
cmd+=['queue_runtime.cpp']
if not arm and platform.system()=='Windows':cmd+=['-Wl,-Bstatic','-lgomp','-Wl,-Bdynamic']
cmd+=['-o',library]
if arm:cmd+=['-ldl']
with (O/'build.log').open('w') as f:r=subprocess.run(cmd,cwd=O,stdout=f,stderr=subprocess.STDOUT)
record=dict(command=cmd,exit=r.returncode,sources_SHA256=hashes,library=str(O/library),SHA256=hashlib.sha256((O/library).read_bytes()).hexdigest() if r.returncode==0 else None,active_library_replaced=False)
(O/'recompile.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2));assert r.returncode==0,(O/'build.log').read_text()[-4000:]
