set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,tarfile,hashlib,os,sys,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_periodic_joint_20261030');identity=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
t=json.loads((identity/'vectors_results_v3/terminal.json').read_text())
s=json.loads((identity/'vectors_results_v3/record.json').read_text())
assert t['status']==s['status']=='ALL132_ACTUAL_ARM_NCNN_VECTORS_PREPROCESS_AND_RETRIEVAL_PASS_FROZEN_GATES'
assert t['model_forwards']==132 and not (Path('/proc')/str(t['PID'])).exists() and sha(identity/'vectors_results_v3/record.json')==t['record_sha256']
assert not (root/'launch.json').exists() and not (root/'results').exists()
archive=root/'payload.tar.gz';assert sha(archive)=='6127f6ea26ca1267163bd6b478ddc18705b08471edf126db276bb13dd4ddd9c4'
with tarfile.open(archive) as tar:
 assert len(tar.getmembers())==397
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(root/m.name).resolve();assert p.is_relative_to(root.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
p=json.loads((root/'protocol_template.json').read_text());assert sha(root/'protocol_template.json')=='741eb395604d38b3701bb4eefd95a1c2971079118f384b8405bcd167e380a427'
patch=root/'patch_v2.tar.gz';assert sha(patch)=='f983a9c459b161d52cd0684ed2fd09c7cb5baa416e671f32d9d673e7a51a3b8f'
with tarfile.open(patch) as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['background_worker_v2.py','board_periodic_v2.py','protocol_template_v2.json']
  f=root/m.name;assert not f.exists();f.write_bytes(tar.extractfile(m).read())
assert sha(root/'protocol_template_v2.json')=='8c9777c0afe8fe3a278de3ad6f26dd75528b173afe55a3633fab31d00bf4ae45'
p=json.loads((root/'protocol_template_v2.json').read_text())
roots=[identity/'libcow_encoder_v2.so',identity/'encoder.ncnn.param',identity/'encoder.ncnn.bin',identity/'ncnn_encoder_v3.py',
 identity/'vectors_results_v3/all_normalized_features.npz',identity/'image_groups.json',identity/'vectors_results_v3/record.json']
port=Path('/home/xilinx/jupyter_notebooks/cow_research_numpy_tracker_20261029')
roots.extend([port/'frame_pipeline.py',*sorted((port/'cow_tracker').glob('*.py'))])
p['runtime_files']=[{'file':str(file),'sha256':sha(file)} for file in roots]
p['runtime_binding_status']='QUALIFIED_A9_ENCODER_AND_COUNTER_FILES_HASHED_BEFORE_CHILD_START'
protocol=root/'protocol.json';assert not protocol.exists();protocol.write_text(json.dumps(p,indent=2)+'\n')
with (root/'run.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_periodic_v2.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'protocol_sha256':sha(protocol),'period_ns':200000000,'slots_per_case':392,'cases':2,
 'actual_frontend_and_actual_background_same_board':True,'highres_and_RFID_are_public_replay_and_simulation':True}
(root/'launch.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
