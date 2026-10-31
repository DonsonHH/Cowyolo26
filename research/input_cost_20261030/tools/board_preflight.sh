set -euo pipefail
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,fcntl,socket,os
from pynq import PL
root=Path('/home/xilinx/jupyter_notebooks/cow_research_causal_photo_20261030');p=json.loads((root/'run_protocol.json').read_text());t=json.loads((root/'results/terminal.json').read_text());c=json.loads((root/'collection_terminal.json').read_text())
assert t['status']=='ALL_SIX392_SLOT_CAUSAL_PHOTO_SAME_BOARD_REPEATS_COMPLETE' and c['status']=='RESULT_ARCHIVE_COMPLETE'
assert not (Path('/proc')/str(t['PID'])).exists() and not (Path('/proc')/str(c['PID'])).exists()
for run in p['runs']:
 if run['policy']=='foreground_only':continue
 q=json.loads((root/'results'/run['run']/'background/terminal.json').read_text());assert not (Path('/proc')/str(q['PID'])).exists()
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
digest=hashlib.sha256(Path(PL.bitfile_name).read_bytes()).hexdigest();assert digest==p['O8_bit_sha256']
ports={}
for port in [22,9090]:
 try:s=socket.create_connection(('127.0.0.1',port),timeout=1);s.close();ports[str(port)]=True
 except OSError:ports[str(port)]=False
assert hasattr(os,'posix_fadvise') and hasattr(os,'POSIX_FADV_DONTNEED')
print(json.dumps({'status':'PRIOR_CAUSAL_TASK_AND_WORKERS_ABSENT_ORIGINAL_O8_LOCK_AND_FADVISE_READY','PL_bitfile':PL.bitfile_name,'PL_bit_sha256':digest,'services':ports,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'memory':Path('/proc/meminfo').read_text(),'new_forwards':0,'PL_programming':False}))
PY
