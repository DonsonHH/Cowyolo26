from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
diagnostic=json.loads(json.loads((ROOT/'evidence/board_native_exit_diagnostic.json').read_text())['stdout']);assert diagnostic['returncode']==-4 and 'before_native_create' in diagnostic['stdout'] and 'native_create_finished' not in diagnostic['stdout']
inspection=json.loads(json.loads((ROOT/'evidence/board_native_exit_inspection.json').read_text())['stdout']);assert 'VFPv4' in inspection['readelf_attributes']
p=json.loads((ROOT/'protocol/board_build_v1.json').read_text());p.update({'status':'FROZEN_A9_VFPV3_NEON_REPAIR_BEFORE_REBUILD',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'previous_build_and_library_preserved':True,'explicit_new_CMake_options':['-DNCNN_VFPV4=OFF'],
 'old_actual_diagnostic_exit_signal':4,'old_failure_layer':'NCNN native create, before any full image network run',
 'cause_evidence':'NCNN_RUNTIME_CPU=OFF with default NCNN_VFPV4=ON appends -mfpu=neon-vfpv4 in officialsrc/CMakeLists; binaryrequiresVFPv4 but boardCPUonlyvfpv3.',
 'model_source_or_numeric_tolerance_changes':False})
p['CMake_options'].append('-DNCNN_VFPV4=OFF')
protocol=ROOT/'protocol/board_build_v2.json';protocol.write_text(json.dumps(p,indent=2)+'\n')
build=(ROOT/'tools/build_ncnn_board.py').read_text();build=build.replace("ROOT/'build_protocol.json'","ROOT/'build_protocol_v2.json'")
build=build.replace("source=ROOT/'source';source.mkdir(exist_ok=False)","source=ROOT/'source';assert source.is_dir()")
start=build.index(" with tarfile.open(ROOT/'ncnn_source.tar.gz') as tar:");end=build.index(" build=ROOT/'build';sdk=ROOT/'install'",start)
build=build[:start]+build[end:]
build=build.replace("build=ROOT/'build';sdk=ROOT/'install'","build=ROOT/'build_v2';sdk=ROOT/'install_v2'")
build=build.replace("ROOT/'libcow_encoder.so'","ROOT/'libcow_encoder_v2.so'")
build=build.replace("'stage_'","'v2_stage_'").replace("'build_result.json'","'build_v2_result.json'").replace("'build_failure.json'","'build_v2_failure.json'").replace("'build_terminal.json'","'build_v2_terminal.json'")
file=ROOT/'tools/build_ncnn_board_v2.py';file.write_text(build,newline='\n')
archive=ROOT/'board_build_v2_patch.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for source,name in [(file,'build_ncnn_board_v2.py'),(protocol,'build_protocol_v2.json')]:tar.add(source,arcname=name,recursive=False)
meta={'bytes':archive.stat().st_size,'sha256':sha(archive),'members':2,'protocol_sha256':sha(protocol),'new_source_extraction':False,'old_library_preserved':True}
(ROOT/'evidence/board_build_v2_payload.json').write_text(json.dumps(meta,indent=2)+'\n')
launch='''set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,tarfile,hashlib,subprocess,sys,os
root=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029')
assert not Path('/proc/31016').exists() and not (root/'build_v2').exists() and not (root/'build_v2_launch.json').exists()
old=json.loads((root/'build_terminal.json').read_text());assert old['success'] and not (Path('/proc')/str(old['PID'])).exists()
d=json.loads((root/'native_crash_diagnostic.json').read_text());assert d['returncode']==-4
archive=root/'build_v2_patch.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['build_ncnn_board_v2.py','build_protocol_v2.json']
  p=root/m.name;assert not p.exists();p.write_bytes(tar.extractfile(m).read())
with (root/'run_build_v2.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-u','-B',str(root/'build_ncnn_board_v2.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'NCNN_VFPV4':False,'CortexA9_NEON_VFPv3':True,'old_native_failure_preserved':True,'global_dependencies_changed':False}
(root/'build_v2_launch.json').write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r))
PY
'''.replace('DIGEST',meta['sha256'])
(ROOT/'tools/launch_build_v2.sh').write_text(launch,newline='\n')
status=(ROOT/'tools/board_build_status.sh').read_text().replace("root/'launch.json'","root/'build_v2_launch.json'").replace('stage_*.log','v2_stage_*.log')
status=status.replace("'build_terminal.json'","'build_v2_terminal.json'").replace("'build_result.json'","'build_v2_result.json'").replace("'build_failure.json'","'build_v2_failure.json'").replace("'run.log'","'run_build_v2.log'")
(ROOT/'tools/build_status_v2.sh').write_text(status,newline='\n');print(json.dumps(meta))
