from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,py_compile
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;CAMERA=ROOT/'camera_delivery'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
manifest=load(CAMERA/'manifest.json');assert len(manifest)==392 and [r['frame0'] for r in manifest]==list(range(8915,10874,5))
files={'camera/manifest.json':CAMERA/'manifest.json','camera/summary.json':CAMERA/'summary.json'}
for row in manifest:
 file=CAMERA/row['file'];assert sha(file)==row['sha256']
 with Image.open(file) as im:im.load();assert im.size==(1050,1440)
 files['camera/'+row['file']]=file
for name in ['tools/board_periodic.py','tools/background_worker.py']:
 py_compile.compile(str(ROOT/name),doraise=True);files[Path(name).name]=ROOT/name
workload=load(ROOT/'protocol/workload_v1.json');identity=load(PROJECT/'pynq_identity_ncnn_20261029/protocol/encoder_v1.json')
evaluation=load(PROJECT/'pynq_rot192_eval_20261029/protocol/board_video_v2.json')
p={'status':'FROZEN_BEFORE_PERIODIC_TWO_CASE_PAYLOAD_UPLOAD','created_UTC':datetime.now(timezone.utc).isoformat(),
 'workload_protocol_sha256':sha(ROOT/'protocol/workload_v1.json'),'period_ns':200000000,'cases':['foreground_only','foreground_with_identity'],
 'video':evaluation['videos'][0],'tracker_config':evaluation['tracker_config'],'counter_kwargs':evaluation['counter_kwargs'],
 'registered_IDs':identity['registered_IDs'],'fixed_identity_threshold':identity['fixed_threshold'],'backend_nice_increment':10,
 'foreground_source_model':evaluation['checkpoint_sha256'],'background_encoder':identity['encoder_condition']['checkpoint_sha256'],
 'O8_bit_sha256':evaluation['O8_bit_sha256'],
 'highres_inputs_lossy':True,'highres_physical_crop_original_xyxy':[870,0,1920,1440],'highres_jpeg_quality':95,
 'source_frame0_first':8915,'source_frame0_last':10870,'offered_slots_per_case':392,
 'runtime_files':[], # Filled by launch gate with current successful A9 build and qualified vector evidence, before child starts.
 'runtime_binding_required_before_start':True,'input_quant256_equivalence_sha256':sha(PROJECT/'pynq_rot192_eval_20261029/results/input_quant256_equivalence.json'),
 'simulated_no_RFID_condition':True,'real_camera_capture_or_permanent_identity_accuracy_claimed':False,
 'source_count_total_control':12,'previous_actual_no_skip_model_count':11,'whole_goal_complete':False,
 'payload_files':[{'file':name,'sha256':sha(file),'bytes':file.stat().st_size} for name,file in sorted(files.items())]}
file=ROOT/'protocol/run_template_v1.json';assert not file.exists();file.write_text(json.dumps(p,indent=2)+'\n');files['protocol_template.json']=file
archive=ROOT/'board_payload.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for name,file in sorted(files.items()):tar.add(file,arcname=name,recursive=False)
meta={'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files),'template_protocol_sha256':sha(ROOT/'protocol/run_template_v1.json')}
(ROOT/'evidence/payload.json').write_text(json.dumps(meta,indent=2)+'\n')
target='/home/xilinx/jupyter_notebooks/cow_research_periodic_joint_20261030'
create='''set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json
root=Path('TARGET');root.mkdir(exist_ok=False);print(json.dumps({'status':'NEW_PERIODIC_JOINT_TASK_DIRECTORY_CREATED','path':str(root)}))
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
import json,tarfile,hashlib,os,sys,subprocess
root=Path('TARGET');identity=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
t=json.loads((identity/'vectors_results_v2/terminal.json').read_text())
s=json.loads((identity/'vectors_results_v2/record.json').read_text())
assert t['status']==s['status']=='ALL132_ACTUAL_ARM_NCNN_VECTORS_PREPROCESS_AND_RETRIEVAL_PASS_FROZEN_GATES'
assert t['model_forwards']==132 and not (Path('/proc')/str(t['PID'])).exists() and sha(identity/'vectors_results_v2/record.json')==t['record_sha256']
assert not (root/'launch.json').exists() and not (root/'results').exists()
archive=root/'payload.tar.gz';assert sha(archive)=='DIGEST'
with tarfile.open(archive) as tar:
 assert len(tar.getmembers())==MEMBERS
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(root/m.name).resolve();assert p.is_relative_to(root.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
p=json.loads((root/'protocol_template.json').read_text());assert sha(root/'protocol_template.json')=='TEMPLATE'
roots=[identity/'libcow_encoder_v2.so',identity/'encoder.ncnn.param',identity/'encoder.ncnn.bin',identity/'ncnn_encoder_v2.py',
 identity/'vectors_results_v2/all_normalized_features.npz',identity/'image_groups.json',identity/'vectors_results_v2/record.json']
roots.extend(Path('/home/xilinx/jupyter_notebooks/cow_research_numpy_tracker_20261029')/r['file'] for r in json.loads((Path('/home/xilinx/jupyter_notebooks/cow_research_numpy_tracker_20261029')/'regression_v1.json').read_text())['files'] if False)
port=Path('/home/xilinx/jupyter_notebooks/cow_research_numpy_tracker_20261029')
roots.extend([port/'frame_pipeline.py',*sorted((port/'cow_tracker').glob('*.py'))])
p['runtime_files']=[{'file':str(file),'sha256':sha(file)} for file in roots]
p['runtime_binding_status']='QUALIFIED_A9_ENCODER_AND_COUNTER_FILES_HASHED_BEFORE_CHILD_START'
protocol=root/'protocol.json';assert not protocol.exists();protocol.write_text(json.dumps(p,indent=2)+'\\n')
with (root/'run.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_periodic.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'protocol_sha256':sha(protocol),'period_ns':200000000,'slots_per_case':392,'cases':2,
 'actual_frontend_and_actual_background_same_board':True,'highres_and_RFID_are_public_replay_and_simulation':True}
(root/'launch.json').write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r))
PY
'''.replace('TARGET',target).replace('DIGEST',meta['sha256']).replace('MEMBERS',str(meta['members'])).replace('TEMPLATE',meta['template_protocol_sha256'])
# Remove an unused generator so launch only binds files actually imported by the run.
launch='\n'.join(line for line in launch.splitlines() if 'roots.extend(Path(' not in line)+'\n'
(ROOT/'tools/launch_board.sh').write_text(launch,newline='\n')
print(json.dumps(meta))
