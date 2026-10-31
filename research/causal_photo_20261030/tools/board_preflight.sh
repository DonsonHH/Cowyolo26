set -euo pipefail
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
from datetime import datetime, timezone
import json,hashlib,fcntl,socket,subprocess
from pynq import PL
base=Path('/home/xilinx/jupyter_notebooks')
old=base/'cow_research_mosaic192_joint_20261030'
p=json.loads((old/'run_protocol.json').read_text());t=json.loads((old/'results/terminal.json').read_text())
assert t['status']=='ALL_SIX392_SLOT_MOSAIC192_SAME_BOARD_REPEATS_COMPLETE'
assert not (Path('/proc')/str(t['PID'])).exists()
children=[]
for run in p['runs']:
 if run['policy']=='foreground_only':continue
 r=json.loads((old/'results'/run['run']/'background/terminal.json').read_text())
 assert not (Path('/proc')/str(r['PID'])).exists()
 children.append({'PID':r['PID'],'proc_exists':False})
lock=(base/'yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
bit=PL.bitfile_name;digest=hashlib.sha256(Path(bit).read_bytes()).hexdigest();assert digest==p['O8_bit_sha256']
ports={}
for port in [22,9090]:
 try:s=socket.create_connection(('127.0.0.1',port),timeout=1);s.close();ports[str(port)]=True
 except OSError:ports[str(port)]=False
camera=Path(p['camera_root']);files=sorted((camera/'highres').glob('*.jpg'));assert len(files)==392
print(json.dumps({'status':'SAME_O8_AND_PRIOR_TERMINAL_READ_LOCK_AVAILABLE','host_UTC_observed_by_client':True,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'prior_PID':t['PID'],'children':children,'PL_bitfile':bit,'PL_bit_sha256':digest,'services':ports,'camera_JPEGs':len(files),'camera_bytes':sum(f.stat().st_size for f in files),'memory':Path('/proc/meminfo').read_text(),'disk':subprocess.run(['df','-B1',str(base)],capture_output=True,text=True).stdout,'video_devices':[str(f) for f in Path('/dev').glob('video*')],'new_forwards':0,'PL_programming':False}))
PY
