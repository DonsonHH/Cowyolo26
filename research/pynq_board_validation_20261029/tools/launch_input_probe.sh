set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,os,sys,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_validation_v2_20261029')
assert not (root/'input_probe').exists() and not (root/'launch_input_probe.json').exists()
for run in ['probe192','formal192','formal256','formal320']:
    t=json.loads((root/run/'terminal.json').read_text());assert t['close_error'] is None and not (Path('/proc')/str(t['PID'])).exists()
with (root/'input_probe.log').open('xb') as f:
    p=subprocess.Popen([sys.executable,'-u','-B',str(root/'board_input_probe.py')],stdout=f,stderr=subprocess.STDOUT,cwd=str(root),env=os.environ.copy(),start_new_session=True)
record={'status':'CPU_ONLY_INPUT_PIXEL_AND_TIMING_PROBE_STARTED','PID':p.pid,'network_forwards':0,'PL_actions':0}
(root/'launch_input_probe.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
PY
