set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,os,subprocess
from pynq import PL
root=Path('/home/xilinx/jupyter_notebooks/yolo26_optimization_8')
paths=['native_graph.py','native_sources/native_queue.so','device_initialize.py','hardware/accepted/optimization_8_resident.bit','hardware/accepted/optimization_8_resident.hwh']
print(json.dumps({'status':'READONLY_FINAL_O8_RUNTIME_SHA_AND_NO_COW_VECTOR_PROCESS','boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'actual_runtime_files':[{'relative':r,'bytes':(root/r).stat().st_size,'sha256':hashlib.sha256((root/r).read_bytes()).hexdigest()} for r in paths],
 'PL_bitfile':PL.bitfile_name,'prior_cow_PID12010_exists':Path('/proc/12010').exists(),'services':subprocess.check_output(['systemctl','is-active','ssh','jupyter'],text=True),
 'new_model_or_hardware_actions':0}))
PY
