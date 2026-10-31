from pathlib import Path
import json,hashlib,tarfile,os,socket,fcntl
from pynq import PL
ROOT=Path(__file__).resolve().parent
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_bytes(json.dumps(v,indent=2).encode()+bytes([10]))
p=load(ROOT/'run_protocol.json');s=load(ROOT/'results/record.json');t=load(ROOT/'results/terminal.json')
assert s['status']==t['status']=='ALL4_ACTUAL_COUNT_TRIGGER_OLD_NEW_NEW_OLD_ASYNC_CAUSAL_IDENTITY_RUNS_COMPLETE'and t['record_sha256']==sha(ROOT/'results/record.json')and t['close_error']is None
assert not(Path('/proc')/str(t['PID'])).exists()and s['qualification_forwards']==8 and s['warmup_forwards']==8
children=[]
for spec in p['runs']:
 folder=ROOT/'results'/spec['run']/'background';b=load(folder/'record.json');done=load(folder/'terminal.json')
 assert b['status']==done['status']=='ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE'and done['record_sha256']==sha(folder/'record.json')and not(Path('/proc')/str(done['PID'])).exists()
 assert b['model_forwards']==len(b['jobs'])and len(b['warmups'])==1
 children.append({'run':spec['run'],'PID':done['PID'],'proc_exists':False,'jobs':len(b['jobs'])})
for row in p['runtime_files']:assert sha(row['file'])==row['sha256']
assert sha(PL.bitfile_name)==p['O8_bit_sha256']
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
for port in[22,9090]:connection=socket.create_connection(('127.0.0.1',port),timeout=2);connection.close()
save(ROOT/'final_board_state.json',{'status':'ALL_TRIGGER_PAIR_PARENTS_CHILDREN_ABSENT_O8_BOUND_MODELS_GALLERIES_LOCK_AND_LOCAL_SERVICES_VERIFIED','parent_PID':t['PID'],'children':children,'collector_PID':os.getpid(),'PL_SHA256':sha(PL.bitfile_name),'all_runtime_hashes_match':True,'shared_lock_available':True,'local_services':{'22':True,'9090':True},'eth0_carrier':Path('/sys/class/net/eth0/carrier').read_text().strip()})
files=sorted([f for f in(ROOT/'results').rglob('*')if f.is_file()],key=lambda x:(x.suffix,x.name,str(x)))+[ROOT/r['file']for r in p['payload_files']]+[ROOT/name for name in['run_protocol.json','launch.json','run.log','final_board_state.json']]
assert len(files)==len(set(files));rows=[{'file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)}for f in files];save(ROOT/'result_manifest.json',rows)
a=ROOT/'trigger_pair_delivery_v1.tar.xz';assert not a.exists()
with tarfile.open(a,'w:xz',preset=3)as tar:
 for f in files+[ROOT/'result_manifest.json']:tar.add(f,arcname=f.relative_to(ROOT).as_posix(),recursive=False)
os.sync();v={'archive':str(a),'bytes':a.stat().st_size,'sha256':sha(a),'members':len(files)+1,'manifest_files':len(rows)};save(ROOT/'transfer.json',v);save(ROOT/'collection_terminal.json',{'status':'TRIGGER_PAIR_ORIGINAL_ARCHIVE_COMPLETE','PID':os.getpid(),'transfer':v});print(json.dumps(v),flush=True)
