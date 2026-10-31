set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,tarfile,hashlib,subprocess,sys,os
root=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029')
t=json.loads((root/'build_v2_terminal.json').read_text());assert t['success'] and not (Path('/proc')/str(t['PID'])).exists()
assert not Path('/proc/31016').exists() and not (root/'vectors_results_v2').exists()
attributes=subprocess.check_output(['readelf','-A',str(root/'libcow_encoder_v2.so')],text=True);assert 'VFPv4' not in attributes and 'Fused-MAC' not in attributes
(root/'A9_library_attributes_v2.txt').write_text(attributes)
archive=root/'vectors_v2_patch.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='830744c21823fd725462ce8e6195370cc30dfc83677604484c28cb9b9cf22f1d'
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['ncnn_encoder_v2.py','board_vectors_v2.py','vectors_protocol_v2.json']
  path=root/m.name;assert not path.exists();path.write_bytes(tar.extractfile(m).read())
with (root/'vectors_v2.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_vectors_v2.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
record={'PID':child.pid,'expected_actual_vectors':132,'warmups':2,'PL_actions':0,'old_failed_PID':31016,'VFPv4_present_in_v2_binary':False}
(root/'vectors_v2_launch.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
PY
