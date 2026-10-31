set -euo pipefail
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,fcntl,os,resource,socket
from pynq import PL
r=Path('/home/xilinx/jupyter_notebooks/cow_research_async_highres_20261030');p=json.loads((r/'run_protocol.json').read_text());t=json.loads((r/'results/terminal.json').read_text());c=json.loads((r/'collection_terminal.json').read_text())
assert t['status']=='ALL_FOUR392_SLOT_SERIAL_ASYNC_HIGHRES_SAME_BOARD_REPEATS_COMPLETE' and c['status']=='RESULT_ARCHIVE_COMPLETE'
assert not (Path('/proc')/str(t['PID'])).exists() and not (Path('/proc')/str(c['PID'])).exists()
for run in p['runs']:
 q=json.loads((r/'results'/run['run']/'background/terminal.json').read_text());assert not (Path('/proc')/str(q['PID'])).exists()
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
digest=hashlib.sha256(Path(PL.bitfile_name).read_bytes()).hexdigest();assert digest==p['O8_bit_sha256']
fields=Path('/proc/self/stat').read_text().rsplit(')',1)[1].split();ticks=int(fields[11])+int(fields[12]);hz=os.sysconf('SC_CLK_TCK');usage=resource.getrusage(resource.RUSAGE_SELF);assert abs(ticks/hz-(usage.ru_utime+usage.ru_stime))<=2/hz
assert os.getpriority(os.PRIO_PROCESS,0)==0
ports={}
for port in [22,9090]:
 try:q=socket.create_connection(('127.0.0.1',port),timeout=1);q.close();ports[str(port)]=True
 except OSError:ports[str(port)]=False
print(json.dumps({'status':'PRIOR_ASYNC_TASK_TERMINAL_ABSENT_SAME_O8_CPU_STAT_AND_LOCK_READY','PL_bit_sha256':digest,'services':ports,'clock_ticks_per_second':hz,'proc_CPU_seconds':ticks/hz,'rusage_CPU_seconds':usage.ru_utime+usage.ru_stime,'affinity':sorted(os.sched_getaffinity(0)),'parent_nice':os.getpriority(os.PRIO_PROCESS,0),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'new_forwards':0}))
PY
