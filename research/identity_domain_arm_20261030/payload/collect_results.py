from pathlib import Path
import json,hashlib,tarfile,os,socket,fcntl
from pynq import PL

ROOT=Path(__file__).resolve().parent
def load(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):assert not path.exists();path.write_text(json.dumps(value,indent=2)+'\n')

plan=load(ROOT/'run_protocol.json');state=load(ROOT/'results/record.json');done=load(ROOT/'results/terminal.json')
assert state['status']==done['status']=='ALL97_NEW_ENCODER_ARM_VECTORS_INPUT_HASHES_AND120_RETENTION_DECISIONS_PASS'
assert done['record_sha256']==sha(ROOT/'results/record.json')and not(Path('/proc')/str(done['PID'])).exists()
assert state['model_forwards']==97 and len(state['warmups'])==2 and sha(PL.bitfile_name)==plan['O8_bit_sha256']
old=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029');assert sha(old/'encoder.ncnn.bin')==plan['default_old_encoder_bin_sha256']
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
for port in[22,9090]:connection=socket.create_connection(('127.0.0.1',port),timeout=2);connection.close()
save(ROOT/'final_board_state.json',{'status':'NEW_ARM_IDENTITY_TASK_TERMINAL_ABSENT_DEFAULT_ENCODER_AND_O8_UNCHANGED',
 'experiment_PID':done['PID'],'experiment_proc_exists':False,'collector_PID':os.getpid(),'PL_bitfile':PL.bitfile_name,'PL_sha256':sha(PL.bitfile_name),
 'default_old_encoder_bin_sha256':sha(old/'encoder.ncnn.bin'),'lock_available':True,'local_services':{'22':True,'9090':True},
 'eth0_carrier':Path('/sys/class/net/eth0/carrier').read_text().strip(),'new_model_forwards_by_collection':0})
files=sorted([path for path in(ROOT/'results').rglob('*')if path.is_file()]+[ROOT/name for name in['run_protocol.json','board_test.py','collect_results.py','launch.json','run.log','final_board_state.json']])
manifest=[{'file':path.relative_to(ROOT).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)}for path in files];save(ROOT/'result_manifest.json',manifest)
archive=ROOT/'new_identity_ARM_delivery_v1.tar.xz';assert not archive.exists()
with tarfile.open(archive,'w:xz',preset=3)as tar:
 for path in files+[ROOT/'result_manifest.json']:tar.add(path,arcname=path.relative_to(ROOT).as_posix(),recursive=False)
os.sync();transfer={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files)}
save(ROOT/'transfer.json',transfer);save(ROOT/'collection_terminal.json',{'status':'NEW_ARM_IDENTITY_FULL_ORIGINAL_ARCHIVE_COMPLETE','PID':os.getpid(),'transfer':transfer});print(json.dumps(transfer),flush=True)
