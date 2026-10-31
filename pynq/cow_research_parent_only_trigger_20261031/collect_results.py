"""Collect the four dynamic-trigger runs only after all processes are terminal."""
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,os,subprocess,tarfile
from pynq import PL,Overlay
ROOT=Path('/home/xilinx/jupyter_notebooks/cow_research_parent_only_trigger_20261031')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
assert sha(ROOT/'run_protocol.json')=='17e08b19b38d438351e005ecc6fa90256f65b7ec8f780aa517449d7c3856af4c'
p=load(ROOT/'run_protocol.json');state=load(ROOT/'results/record.json');end=load(ROOT/'results/terminal.json')
assert state['status']==end['status']=='ALL4_ACTUAL_COUNT_TRIGGER_OLD_NEW_NEW_OLD_ASYNC_CAUSAL_IDENTITY_RUNS_COMPLETE'
assert end['record_sha256']==sha(ROOT/'results/record.json')and end['close_error']is None
assert state['boot_id']==p['expected_boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert not(Path('/proc')/str(end['PID'])).exists()
children=[]
for spec,case in zip(p['runs'],state['cases']):
 folder=ROOT/'results'/spec['run']/'background';worker=load(folder/'record.json');terminal=load(folder/'terminal.json')
 assert terminal['record_sha256']==sha(folder/'record.json')and worker['status']==terminal['status']=='ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE'
 assert not(Path('/proc')/str(terminal['PID'])).exists()
 assert len(worker['warmups'])==1 and worker['model_forwards']==len(worker['jobs'])==case['actual_background_jobs']<=p['maximum_identity_jobs_per_case']
 children.append({'run':spec['run'],'PID':terminal['PID'],'proc_exists':False,'jobs':len(worker['jobs'])})
assert len(children)==len(state['cases'])==4
for row in p['runtime_files']:assert sha(Path(row['file']))==row['sha256']
assert PL.bitfile_name and sha(Path(PL.bitfile_name))==p['O8_bit_sha256']
with Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('rb')as f:
 fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
o=Overlay(PL.bitfile_name,download=False)
hardware={'core_error':hex(o.conv_accel_0.read(0x64)),'DMA_MM2S':hex(o.axi_dma_0.read(4)),'DMA_S2MM':hex(o.axi_dma_0.read(0x34))}
assert hardware['core_error']=='0x0'and not((int(hardware['DMA_MM2S'],16)|int(hardware['DMA_S2MM'],16))&0x770)
services={name:subprocess.run(['systemctl','is-active',name],capture_output=True,text=True).stdout.strip()for name in['ssh','jupyter']}
kernel=subprocess.run(['dmesg'],capture_output=True,text=True)
final={'status':'ALL4_PARENT_ONLY_DYNAMIC_TRIGGER_RESULTS_PROCESSES_RUNTIME_AND_DEVICE_VERIFIED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'boot_id':state['boot_id'],'parent_PID':end['PID'],'parent_absent':True,
 'children':children,'collector_PID':os.getpid(),'PL_SHA256':sha(Path(PL.bitfile_name)),
 'all_runtime_hashes_match':True,'shared_lock_available':True,'hardware':hardware,'services':services,
 'kernel_memory_messages':[line for line in kernel.stdout.splitlines()if any(word in line.lower()for word in['out of memory','oom-kill','killed process','allocation failure'])],
 'new_model_forwards_by_collection':0,'PL_programmed':False}
def save(path,value):
 with path.open('x')as f:json.dump(value,f,indent=2);f.write('\n')
save(ROOT/'final_board_state.json',final)
files=sorted([path for path in(ROOT/'results').rglob('*')if path.is_file()]+[ROOT/row['file']for row in p['payload_files']]+[ROOT/name for name in['run_protocol.json','launch.json','run.log','preflight.json','final_board_state.json']]+[Path(__file__)])
assert len(files)==len(set(files))
manifest=ROOT/'result_manifest.json';save(manifest,[{'file':path.relative_to(ROOT).as_posix(),'bytes':path.stat().st_size,'sha256':sha(path)}for path in files])
archive=ROOT/'parent_only_trigger_delivery_v1.tar.xz';assert not archive.exists()
with tarfile.open(archive,'w:xz',preset=3)as tar:
 for path in files+[manifest]:tar.add(path,arcname=path.relative_to(ROOT).as_posix(),recursive=False)
for row in load(manifest):assert sha(ROOT/row['file'])==row['sha256']
os.sync()
transfer={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files),'new_model_forwards':0}
save(ROOT/'transfer.json',transfer);print(json.dumps(transfer),flush=True)
