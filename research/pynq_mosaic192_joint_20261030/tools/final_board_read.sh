set -euo pipefail
test "$(id -un)" = root
export XILINX_XRT=/usr
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,socket,fcntl
from pynq import PL
tasks=[]
for name in ['cow_research_o8_mosaic192_qual_20261030','cow_research_mosaic192_video_20261030','cow_research_mosaic192_joint_20261030']:
 root=Path('/home/xilinx/jupyter_notebooks')/name;launch=json.loads((root/'launch.json').read_text());pid=launch['PID']
 terminal=json.loads((root/'results/terminal.json').read_text());assert terminal['close_error'] is None and not (Path('/proc')/str(pid)).exists()
 tasks.append({'task':name,'PID':pid,'proc_exists':False,'status':terminal['status']})
joint=Path('/home/xilinx/jupyter_notebooks/cow_research_mosaic192_joint_20261030');p=json.loads((joint/'run_protocol.json').read_text());children=[]
for run in p['runs']:
 if run['policy']=='foreground_only':continue
 root=joint/'results'/run['run']/'background';t=json.loads((root/'terminal.json').read_text());assert t['status']=='ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE'
 assert not (Path('/proc')/str(t['PID'])).exists();children.append({'run':run['run'],'PID':t['PID'],'proc_exists':False})
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
ports={}
for port in [22,9090]:
 try:s=socket.create_connection(('127.0.0.1',port),timeout=1);s.close();ports[str(port)]=True
 except OSError:ports[str(port)]=False
bit=PL.bitfile_name;digest=hashlib.sha256(Path(bit).read_bytes()).hexdigest();assert digest==p['O8_bit_sha256']
print(json.dumps({'status':'THREE_NEW_PARENT_TASKS_FOUR_IDENTITY_WORKERS_TERMINAL_ABSENT_O8_AND_SERVICES_READ',
 'tasks':tasks,'children':children,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'PL_bitfile':bit,'PL_bit_sha256':digest,
 'shared_accelerator_lock_available':True,'services':ports,'video_devices':[str(f) for f in Path('/dev').glob('video*')],
 'new_network_forwards':0,'new_PL_programming':False,'new_runtime_mutations':0}))
PY
