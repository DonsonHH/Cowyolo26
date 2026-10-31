from pathlib import Path
import os,json,hashlib,tarfile,socket,fcntl
from pynq import PL
ROOT=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n')
p=load(ROOT/'run_protocol.json');s=load(ROOT/'results/record.json');done=load(ROOT/'results/terminal.json')
assert done['record_sha256']==sha(ROOT/'results/record.json')and not(Path('/proc')/str(done['PID'])).exists()
for row in p['runtime_files']:assert sha(row['file'])==row['sha256']
assert sha(PL.bitfile_name)==p['O8_bit_sha256']
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
for port in[22,9090]:connection=socket.create_connection(('127.0.0.1',port),timeout=2);connection.close()
save(ROOT/'final_board_state.json',{'status':'FINAL20_ARM_TASK_TERMINAL_ALL_BOUND_RUNTIME_O8_DEFAULT_ENCODER_LOCK_SERVICES_CHECKED','experiment_status':s['status'],'experiment_PID':done['PID'],'experiment_proc_exists':False,'collector_PID':os.getpid(),'PL_bitfile':PL.bitfile_name,'PL_SHA256':sha(PL.bitfile_name),'all_runtime_hashes_match':True,'shared_lock_available':True,'local_services':{'22':True,'9090':True},'eth0_carrier':Path('/sys/class/net/eth0/carrier').read_text().strip(),'new_model_forwards':0})
files=sorted([f for f in(ROOT/'results').rglob('*')if f.is_file()]+[ROOT/name for name in['run_protocol.json','board_evaluate.py','collect_results.py','launch.json','run.log','final_board_state.json']])
manifest=[{'file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)}for f in files];save(ROOT/'result_manifest.json',manifest)
archive=ROOT/'final20_ARM_delivery_v1.tar.xz';assert not archive.exists()
with tarfile.open(archive,'w:xz',preset=3)as tar:
 for f in files+[ROOT/'result_manifest.json']:tar.add(f,arcname=f.relative_to(ROOT).as_posix(),recursive=False)
os.sync();transfer={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files),'experiment_status':s['status']};save(ROOT/'transfer.json',transfer);save(ROOT/'collection_terminal.json',{'status':'FINAL20_ARM_ORIGINAL_ARCHIVE_COMPLETE','PID':os.getpid(),'transfer':transfer});print(json.dumps(transfer),flush=True)
