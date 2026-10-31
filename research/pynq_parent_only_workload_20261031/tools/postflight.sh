set -euo pipefail
test "$(id -un)" = root
XILINX_XRT=/usr /usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import fcntl,hashlib,json,subprocess
from pynq import PL,Overlay
root=Path('/home/xilinx/jupyter_notebooks/cow_research_parent_only_workload_20261031')
p=json.loads((root/'run_protocol.json').read_text());final=json.loads((root/'final_state.json').read_text())
assert not(Path('/proc')/str(final['parent_PID'])).exists()
for row in final['children']:assert not(Path('/proc')/str(row['PID'])).exists()
collection=json.loads((root/'collection_launch.json').read_text());assert not(Path('/proc')/str(collection['PID'])).exists()
with Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('rb')as f:
 fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
assert PL.bitfile_name and hashlib.sha256(Path(PL.bitfile_name).read_bytes()).hexdigest()==p['O8_bit_sha256']
overlay=Overlay(PL.bitfile_name,download=False)
kernel=subprocess.run(['dmesg'],capture_output=True,text=True)
print(json.dumps({'status':'READONLY_AFTER_ALL_EIGHT_RESULTS_COLLECTED_ALL_TASK_PROCESSES_ABSENT',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'parent_and_all8_children_and_collector_absent':True,'lock_available':True,
 'core_error':hex(overlay.conv_accel_0.read(0x64)),
 'DMA_MM2S':hex(overlay.axi_dma_0.read(4)),'DMA_S2MM':hex(overlay.axi_dma_0.read(0x34)),
 'services':{name:subprocess.run(['systemctl','is-active',name],capture_output=True,text=True).stdout.strip()for name in['ssh','jupyter']},
 'kernel_memory_messages':[line for line in kernel.stdout.splitlines()if any(word in line.lower()for word in['out of memory','oom-kill','killed process','allocation failure'])],
 'kernel_log_returncode':kernel.returncode,'new_model_forwards':0,'PL_programmed':False}),flush=True)
PY
