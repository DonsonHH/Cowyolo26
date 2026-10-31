set -euo pipefail
test "$(id -un)" = root
XILINX_XRT=/usr /usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,subprocess
from pynq import PL,Overlay
base=Path('/home/xilinx/jupyter_notebooks');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
previous=base/'cow_research_parent_only_workload_20261031'
final=json.loads((previous/'final_state.json').read_text())
assert not(Path('/proc')/str(final['parent_PID'])).exists()
for row in final['children']:assert not(Path('/proc')/str(row['PID'])).exists()
collection=json.loads((previous/'collection_launch.json').read_text());assert not(Path('/proc')/str(collection['PID'])).exists()
with(base/'yolo26_stage_d/reports/accelerator_job.lock').open('rb')as f:
 fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
assert PL.bitfile_name and sha(Path(PL.bitfile_name))=='5da7a73bf52fd5153e25de5c28a40e2080c29e960d767008e0e804ec527bbfd8'
o=Overlay(PL.bitfile_name,download=False)
hardware={'core_error':hex(o.conv_accel_0.read(0x64)),'DMA_MM2S':hex(o.axi_dma_0.read(4)),'DMA_S2MM':hex(o.axi_dma_0.read(0x34))}
assert hardware['core_error']=='0x0' and not((int(hardware['DMA_MM2S'],16)|int(hardware['DMA_S2MM'],16))&0x770)
sources=[]
for folder in[base/'cow_research_ncnn_identity_20261029/vectors_results_v3',base/'cow_research_mosaic192_video_20261030/results']:
 terminal=json.loads((folder/'terminal.json').read_text());record=json.loads((folder/'record.json').read_text())
 assert terminal['record_sha256']==sha(folder/'record.json') and terminal['status']==record['status']
 sources.append({'folder':str(folder),'record_sha256':sha(folder/'record.json'),'terminal_sha256':sha(folder/'terminal.json'),
                 'status':record['status'],'historical_PID':terminal['PID'],'historical_boot_id':record.get('boot_id'),
                 'historical_PID_not_compared_across_boots':True})
processes=[]
for path in Path('/proc').iterdir():
 if not path.name.isdigit():continue
 try:
  args=(path/'cmdline').read_bytes().split(bytes([0]))
  if any(a.startswith(b'/home/xilinx/jupyter_notebooks/cow_research_')and a.endswith(b'.py')for a in args):
   processes.append({'PID':int(path.name),'args':[a.decode(errors='replace')for a in args]})
 except(OSError,PermissionError):pass
assert not processes,processes
print(json.dumps({'status':'READONLY_ACTUAL_TRIGGER_PARENT_ONLY_PREFLIGHT',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'PL_SHA256':sha(Path(PL.bitfile_name)),'hardware':hardware,'sources':sources,'active_task_processes':processes,
 'shared_lock_available':True,'memory':Path('/proc/meminfo').read_text(),
 'services':{name:subprocess.run(['systemctl','is-active',name],capture_output=True,text=True).stdout.strip()for name in['ssh','jupyter']},
 'new_model_forwards':0,'PL_programmed':False}),flush=True)
PY
