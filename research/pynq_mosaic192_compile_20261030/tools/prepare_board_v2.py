from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,ast
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
q=ROOT/'delivery/results/qualification';s=load(q/'summary.json');p=load(ROOT/'protocol/compile_v1.json')
assert s['all_native_CPU_parity_gates_pass'] and s['primary_ordered_vectors_byte_exact']==8
assert s['checkpoint_sha256']==p['source_checkpoint_sha256']=='628db893fa8be090df206b32c35d8b81839eab2f497925ccbd0c6d855ad9d3eb'
out=ROOT/'board_payload_v2';out.mkdir(exist_ok=False);files=[]
for relative,target in [('compiled/program/graph.bin','program/graph.bin'),('compiled/program/program.json','program/program.json'),('resident_plan_all/resident_plan.bin','resident_plan/resident_plan.bin'),('resident_plan_all/resident_plan.json','resident_plan/resident_plan.json')]:
    f=out/target;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes((q/relative).read_bytes());files.append(f)
for i in range(8):
    f=out/'vectors'/('parity_train_'+str(i)+'.npz');f.parent.mkdir(exist_ok=True);f.write_bytes((q/f.name).read_bytes());files.append(f)
old=PROJECT/'pynq_rot192_compile_20261029/tools/board_cow_vectors.py'
script=ROOT/'tools/board_cow_vectors.py';assert script.exists() and sha(script)==sha(old);ast.parse(script.read_text(encoding='utf-8'))
f=out/script.name;f.write_bytes(script.read_bytes());files.append(f)
protocol={'status':'FROZEN_BEFORE_MOSAIC050_SEED26_REAL_O8_VECTOR_QUALIFICATION','created_host_UTC':datetime.now(timezone.utc).isoformat(),
    'size':192,'class_count':1,'primary_model':'mosaic050_seed26','model_checkpoint_sha256':s['checkpoint_sha256'],'qualification_summary_sha256':sha(q/'summary.json'),
    'expected_O8_bit_sha256':p['expected_O8_bit_sha256'],'parity_gate':{'box_max_absolute_pixels':p['native_output_parity_gate']['box_max_absolute_pixels'],'score_max_absolute':p['native_output_parity_gate']['score_max_absolute'],'classes_exact':p['native_output_parity_gate']['class_exact']},
    'vectors':8,'warmups':2,'expected_model_forwards':10,'all_input_images_from_train_calibration':True,
    'source_video_Toros_or_development_validation_images_used':False,'real_video_count_accuracy_claimed':False,
    'background_identity_active':False,'reference_primary':'previously_frozen_ordered_FP32_nonconv_and_fixed_integerConv_contract',
    'legacy_numpy_reference_retained_in_vector_files':True,'existing_O8_hardware_must_already_be_loaded':True,'new_bitstream_programming':False,
    'original_O8_directory_modified':False,'payload_files':[{'file':f.relative_to(out).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files],
    'whole_goal_complete':False}
# The native gate uses the exact established field names, not a renamed margin.
assert protocol['parity_gate']=={'box_max_absolute_pixels':.002,'score_max_absolute':.0001,'classes_exact':True}
save(ROOT/'protocol/board_vectors_v2.json',protocol)
f=out/'protocol.json';f.write_bytes((ROOT/'protocol/board_vectors_v2.json').read_bytes());files.append(f)
a=ROOT/'board_vectors_payload_v2.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
    for f in files:tar.add(f,arcname=f.relative_to(out).as_posix(),recursive=False)
record={'bytes':a.stat().st_size,'sha256':sha(a),'members':len(files),'protocol_sha256':sha(ROOT/'protocol/board_vectors_v2.json'),
    'board_task_root':'/home/xilinx/jupyter_notebooks/cow_research_o8_mosaic192_qual_20261030'}
save(ROOT/'evidence/board_payload_staging_v2.json',record)
board_root=record['board_task_root']
create='''set -euo pipefail
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json
root=Path('TASK');root.mkdir(exist_ok=False)
print(json.dumps({'status':'NEW_MOSAIC192_TASK_DIRECTORY_CREATED','root':str(root),'new_PL_or_model_actions':0}))
PY
'''.replace('TASK',board_root)
f=ROOT/'tools/create_board_task.sh';assert not f.exists();f.write_text(create,encoding='utf-8',newline='\n')
launch='''set -euo pipefail
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export PYTHONDONTWRITEBYTECODE=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess,os,sys
root=Path('TASK');a=root/'payload.tar.gz'
assert hashlib.sha256(a.read_bytes()).hexdigest()=='PAYLOAD'
assert not (root/'launch.json').exists() and not (root/'results').exists()
with tarfile.open(a) as tar:
 assert len(tar.getmembers())==MEMBERS
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=(root/m.name).resolve();assert f.is_relative_to(root.resolve()) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
assert hashlib.sha256((root/'protocol.json').read_bytes()).hexdigest()=='PROTOCOL'
protocol=json.loads((root/'protocol.json').read_text())
for row in protocol['payload_files']:
 f=root/row['file'];assert f.stat().st_size==row['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==row['sha256']
with (root/'run.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-u','-B',str(root/'board_cow_vectors.py')],stdout=log,stderr=subprocess.STDOUT,cwd=str(root),env=os.environ.copy(),start_new_session=True)
r={'status':'REAL_MOSAIC192_O8_VECTOR_WORKER_STARTED','PID':child.pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'size':192,'class_count':1,'primary_model':'mosaic050_seed26','expected_actual_model_forwards':10,'new_bitstream_programming':False}
with (root/'launch.json').open('x') as f:json.dump(r,f,indent=2);f.write('\\n');f.flush();os.fsync(f.fileno())
print(json.dumps(r))
PY
'''.replace('TASK',board_root).replace('PAYLOAD',record['sha256']).replace('PROTOCOL',record['protocol_sha256']).replace('MEMBERS',str(record['members']))
f=ROOT/'tools/launch_board.sh';assert not f.exists();f.write_text(launch,encoding='utf-8',newline='\n')
status=(PROJECT/'pynq_rot192_compile_20261029/tools/status_board_vectors.sh').read_text(encoding='utf-8').replace('/home/xilinx/jupyter_notebooks/cow_research_o8_rot192_qual_20261029',board_root)
f=ROOT/'tools/status_board.sh';assert not f.exists();f.write_text(status,encoding='utf-8',newline='\n')
collect=(PROJECT/'pynq_rot192_compile_20261029/tools/collect_board_vectors.sh').read_text(encoding='utf-8').replace('/home/xilinx/jupyter_notebooks/cow_research_o8_rot192_qual_20261029',board_root)
f=ROOT/'tools/collect_board.sh';assert not f.exists();f.write_text(collect,encoding='utf-8',newline='\n')
print(json.dumps(record))
