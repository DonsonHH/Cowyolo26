set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export PYTHONDONTWRITEBYTECODE=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,os,sys,subprocess,hashlib
root=Path('/home/xilinx/jupyter_notebooks/cow_research_validation_v2_20261029')
assert not (root/'stream_replay').exists() and not (root/'launch_stream_replay.json').exists()
terminal=json.loads((root/'input_probe/terminal.json').read_text());assert terminal['status']=='BOARD_INPUT12_NATIVE_AND36_LETTERBOX_CONDITIONS_COMPLETE'
assert not (Path('/proc')/str(terminal['PID'])).exists(),'CPUtimingprobestillpresent'
assert hashlib.sha256((root/'stream_protocol.json').read_bytes()).hexdigest()=='b339710040e4f20e1813f50e0c611660f4928c973c7e9115e8f12503e0ce6415'
with (root/'stream_replay.log').open('xb') as log:
    process=subprocess.Popen([sys.executable,'-u','-B',str(root/'board_stream_replay.py')],stdout=log,stderr=subprocess.STDOUT,cwd=str(root),env=os.environ.copy(),start_new_session=True)
result={'status':'ACTUAL_BOARD_LOWRES_PERIODIC_REPLAY_PROCESS_STARTED','PID':process.pid,'offered_slots_each_size':100,
        'sizes':[192,256,320],'offered_Hz':5,'background_identity_active':False,'camera_active':False,
        'script_sha256':hashlib.sha256((root/'board_stream_replay.py').read_bytes()).hexdigest()}
with (root/'launch_stream_replay.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps(result))
PY
