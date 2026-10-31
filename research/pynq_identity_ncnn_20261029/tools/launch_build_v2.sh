set -eu
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
archive=root/'build_v2_patch.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='e33b8e863123cdadf712e18fefee088852f7af2e1bfdc4e3cc99c175c294c878'
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['build_ncnn_board_v2.py','build_protocol_v2.json']
  p=root/m.name;assert not p.exists();p.write_bytes(tar.extractfile(m).read())
with (root/'run_build_v2.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-u','-B',str(root/'build_ncnn_board_v2.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'NCNN_VFPV4':False,'CortexA9_NEON_VFPv3':True,'old_native_failure_preserved':True,'global_dependencies_changed':False}
(root/'build_v2_launch.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
