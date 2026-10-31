set -euo pipefail
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,socket,fcntl
from pynq import PL
root=Path('/home/xilinx/jupyter_notebooks/cow_research_backend_service_20261030');p=json.loads((root/'run_protocol.json').read_text());t=json.loads((root/'results/terminal.json').read_text());ct=json.loads((root/'collection_terminal.json').read_text())
assert t['status']=='ALL_FOUR392_SLOT_IDLE_LOW_PRIORITY_BACKEND_SAME_BOARD_REPEATS_COMPLETE' and ct['status']=='RESULT_ARCHIVE_COMPLETE'
assert not (Path('/proc')/str(t['PID'])).exists() and not (Path('/proc')/str(ct['PID'])).exists()
children=[]
for run in p['runs']:
 if run['policy']=='foreground_only':continue
 q=json.loads((root/'results'/run['run']/'background/terminal.json').read_text());assert q['status']=='ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE' and not (Path('/proc')/str(q['PID'])).exists()
 children.append({'run':run['run'],'PID':q['PID'],'proc_exists':False})
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
ports={}
for port in [22,9090]:
 try:s=socket.create_connection(('127.0.0.1',port),timeout=1);s.close();ports[str(port)]=True
 except OSError:ports[str(port)]=False
bit=PL.bitfile_name;digest=hashlib.sha256(Path(bit).read_bytes()).hexdigest();assert digest==p['O8_bit_sha256']
print(json.dumps({'status':'BACKEND_SERVICE_PARENT_FOUR_WORKERS_AND_COLLECTOR_TERMINAL_ABSENT_O8_AND_SERVICES_READ','task_PID':t['PID'],'collector_PID':ct['PID'],'parents_proc_exists':False,'children':children,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'PL_bitfile':bit,'PL_bit_sha256':digest,'shared_accelerator_lock_available':True,'services':ports,'new_network_forwards':0,'new_PL_programming':False}))
PY
