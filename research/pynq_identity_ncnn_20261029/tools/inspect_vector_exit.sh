set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029')
cache=(root/'build/CMakeCache.txt').read_text()
result={'vector_PID_exists':Path('/proc/31016').exists(),'files':sorted(p.name for p in (root/'vectors_results').glob('*')),
 'dmesg_tail':subprocess.run(['dmesg','--ctime'],capture_output=True,text=True).stdout[-7000:],
 'cpuinfo':Path('/proc/cpuinfo').read_text(),'memory':Path('/proc/meminfo').read_text(),
 'selected_CMake_cache_lines':[line for line in cache.splitlines() if any(k in line for k in ['NCNN_VFPV4','NCNN_ARM','CMAKE_CXX_FLAGS','NCNN_RUNTIME_CPU'])],
 'readelf_attributes':subprocess.run(['readelf','-A',str(root/'libcow_encoder.so')],capture_output=True,text=True).stdout}
print(json.dumps(result))
PY
