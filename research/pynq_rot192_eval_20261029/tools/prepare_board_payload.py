from pathlib import Path
from datetime import datetime,timezone
from PIL import Image
import json,hashlib,tarfile,py_compile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;Q=ROOT/'delivery/results/quality_v2'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=load(ROOT/'protocol/eval_v2.json');s=load(Q/'summary.json');assert s['ORT_actual_forwards']=={'FP32':4225,'QDQ':4225}
assert s['actual_NN_anchor_pixel_checks']==8
manifest=load(Q/'board_input_manifest.json');assert len(manifest)==2654
files={};anchors=0;bytes_total=0
for row in manifest:
 file=Q/row['file'];assert sha(file)==row['sha256']
 with Image.open(file) as im:
  assert im.size==(192,192);rgb=np.asarray(im.convert('RGB'))
 x=np.ascontiguousarray(rgb.transpose(2,0,1)[None],dtype=np.float32)*np.float32(1/255)
 assert hashlib.sha256(x.tobytes()).hexdigest()==row['input_tensor_sha256']
 if row['anchor']:
  expectedfile=PROJECT/'factorial_lane_crop_20261029/delivery/results/roi/pixel_controls'/(row['scene']+'_f'+str(row['frame0'])+'_s192_NN.npz')
  with np.load(expectedfile) as a:assert x[0].tobytes()==a['actual_input'].tobytes()
  anchors+=1
 files[row['file']]=file;bytes_total+=file.stat().st_size
assert anchors==8
for row in load(Q/'native_integer_anchors.json'):
 file=Q/row['file'];assert sha(file)==row['sha256'];files[row['file']]=file
 with np.load(file) as a:
  assert hashlib.sha256(a['input'].tobytes()).hexdigest()==row['input_tensor_sha256']
  assert hashlib.sha256(a['native_integer_raw'].tobytes()).hexdigest()==row['native_integer_raw_sha256']
for file,name in [(Q/'board_input_manifest.json','board_input_manifest.json'),(ROOT/'tools/board_video.py','board_video.py'),(ROOT/'tools/frozen_input.py','frozen_input.py')]:files[name]=file
py_compile.compile(str(ROOT/'tools/board_video.py'),doraise=True)
tracker=load(PROJECT/'pynq_frontend_port_20261029/regression_v1.json')
protocol={'status':'FROZEN_BEFORE2654_ACTUAL_BOARD_VIDEO_FORWARDS','created_UTC':datetime.now(timezone.utc).isoformat(),
 'checkpoint_sha256':p['checkpoint_sha256'],'graph_sha256':p['compiled_graph_sha256'],'resident_plan_sha256':p['resident_plan_sha256'],
 'O8_bit_sha256':'5da7a73bf52fd5153e25de5c28a40e2080c29e960d767008e0e804ec527bbfd8',
 'evaluation_protocol_sha256':sha(ROOT/'protocol/eval_v2.json'),'server_quality_summary_sha256':sha(Q/'summary.json'),
 'confidence':.2,'videos':p['videos'],'tracker_config':tracker['tracker_config'],'counter_kwargs':p['counter_kwargs'],
 'tracker_files':tracker['files'],'all2654_PNG_tensors_independently_verified':True,'8_tensors_byte_exact_to_frozen_GPU_inputs':True,
 'board_real_network_video_forwards_expected':2654,'warmups':2,'counter_paths_expected':6,
 'scope':'Unpaced actual model and counter video replay from server-prepared lossless192PNG. No live camera, 5Hz scheduler or simultaneous identity claimed.',
 'new_training_updates':0,'model_threshold_crop_or_calibration_changed':False,'whole_goal_complete':False,
 'payload_files':[{'file':name,'bytes':file.stat().st_size,'sha256':sha(file)} for name,file in sorted(files.items())]}
file=ROOT/'protocol/board_video_v1.json';assert not file.exists();file.write_text(json.dumps(protocol,indent=2)+'\n');files['board_protocol.json']=file
archive=ROOT/'board_video_payload.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for name,file in sorted(files.items()):tar.add(file,arcname=name,recursive=False)
meta={'sha256':sha(archive),'bytes':archive.stat().st_size,'members':len(files),'protocol_sha256':sha(ROOT/'protocol/board_video_v1.json'),
 'input_PNGs':2654,'PNG_uncompressed_total_file_bytes':bytes_total,'input_tensors_independently_hashed':2654,'prior_GPU_anchor_inputs_byte_exact':8}
(ROOT/'evidence/board_payload.json').write_text(json.dumps(meta,indent=2)+'\n')
target='/home/xilinx/jupyter_notebooks/cow_research_rot192_video_20261029'
create='''set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json
p=Path('TARGET');p.mkdir(exist_ok=False);print(json.dumps({'status':'ACTUAL_VIDEO_TASK_DIRECTORY_CREATED','path':str(p),'model_or_PL_actions':0}))
PY
'''.replace('TARGET',target)
(ROOT/'tools/create_board_task.sh').write_text(create,newline='\n')
launch='''set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess,sys,os
root=Path('TARGET');archive=root/'payload.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
assert not (root/'launch.json').exists() and not (root/'results').exists()
with tarfile.open(archive) as tar:
 assert len(tar.getmembers())==MEMBERS
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  path=(root/m.name).resolve();assert path.is_relative_to(root.resolve()) and not path.exists()
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(m).read())
assert hashlib.sha256((root/'board_protocol.json').read_bytes()).hexdigest()=='PROTO'
with (root/'run.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-u','-B',str(root/'board_video.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
record={'PID':child.pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'actual_video_model_forwards_expected':2654,
 'warmups':2,'counter_paths_expected':6,'scope':'Unpaced PNG replay, actual O8 model and actual ARM counters; not livecamera or simultaneous identity.'}
(root/'launch.json').write_text(json.dumps(record,indent=2)+'\\n');print(json.dumps(record))
PY
'''.replace('TARGET',target).replace('DIGEST',meta['sha256']).replace('MEMBERS',str(meta['members'])).replace('PROTO',meta['protocol_sha256'])
(ROOT/'tools/launch_board.sh').write_text(launch,newline='\n')
print(json.dumps(meta))
