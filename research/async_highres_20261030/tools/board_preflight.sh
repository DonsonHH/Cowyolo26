set -euo pipefail
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,fcntl,socket
from pynq import PL
base=Path('/home/xilinx/jupyter_notebooks');tasks=[]
for name,status in [('cow_research_input_cost_20261030','FAILED'),('cow_research_input_cost_v2_20261030','ALL256_JPEG_READ_CASES128_REAL_O8_AFTER_READS_AND16_RAW_IMAGES_COMPLETE')]:
 t=json.loads((base/name/'results/terminal.json').read_text());assert t['status']==status and not (Path('/proc')/str(t['PID'])).exists();tasks.append({'PID':t['PID'],'proc_exists':False,'status':status})
p=json.loads((base/'cow_research_causal_photo_20261030/run_protocol.json').read_text());digest=hashlib.sha256(Path(PL.bitfile_name).read_bytes()).hexdigest();assert digest==p['O8_bit_sha256']
lock=(base/'yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
ports={}
for port in [22,9090]:
 try:c=socket.create_connection(('127.0.0.1',port),timeout=1);c.close();ports[str(port)]=True
 except OSError:ports[str(port)]=False
print(json.dumps({'status':'INPUT_BENCHMARKS_TERMINAL_ABSENT_SAME_O8_AND_LOCK_READY','tasks':tasks,'PL_bit_sha256':digest,'services':ports,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'memory':Path('/proc/meminfo').read_text(),'new_forwards':0}))
PY
