set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,os,subprocess
import pynq
root=Path('/home/xilinx/jupyter_notebooks/cow_research_lowres_20261029')
def read(path):
    try:return Path(path).read_text(errors='replace')[:12000]
    except Exception as e:return {'error':type(e).__name__,'detail':str(e)[:200]}
def run(args):
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=8)
    return {'exit_code':result.returncode,'output':result.stdout[-16000:]}
files=[]
for f in sorted(root.rglob('*')):
    if f.is_file() and '__pycache__' not in f.parts:
        files.append({'relative':f.relative_to(root).as_posix(),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
record={'board_UTC_may_be_wrong':datetime.now(timezone.utc).isoformat(),'uid':os.getuid(),'boot_id':read('/proc/sys/kernel/random/boot_id'),
        'uptime':read('/proc/uptime'),'pynq_version':pynq.__version__,'PL_bitfile':pynq.PL.bitfile_name,'PL_IP_names':list(pynq.PL.ip_dict),
        'fpga_manager_state':read('/sys/class/fpga_manager/fpga0/state'),'memory':read('/proc/meminfo'),
        'prior_test_files':files,'prior_launch':read(root/'launch.json'),'prior_progress':read(root/'results/progress.json'),
        'prior_size192':read(root/'results/size192.json'),'prior_summary':read(root/'results/summary.json'),'prior_log':read(root/'benchmark.log'),
        'prior_PID8082':run(['ps','-p','8082','-o','pid,ppid,state,etimes,rss,comm']),
        'boot_kernel_tail':run(['journalctl','-k','-b','--no-pager','-n','100']),
        'previous_boot_kernel_tail':run(['journalctl','-k','-b','-1','--no-pager','-n','80']),
        'services':run(['systemctl','is-active','ssh','jupyter']),
        'new_inference_calls':0,'new_overlay_loads':0,'new_training_updates':0}
print(json.dumps(record))
PY
