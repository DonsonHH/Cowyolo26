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
assert not (root/'framebank_replay').exists() and not (root/'launch_framebank_replay.json').exists()
terminal=json.loads((root/'stream_replay/terminal.json').read_text());assert terminal['status']=='ALL3_REAL_BOARD_PERIODIC_LOWRES_REPLAYS_COMPLETED'
assert not (Path('/proc')/str(terminal['PID'])).exists(),'CPUtimingprobestillpresent'
assert hashlib.sha256((root/'framebank_protocol.json').read_bytes()).hexdigest()=='e6e08391cc4dc8c5f97b71767d196bc6ab2f6327a600be7db4f3d23c97a34d4f'
with (root/'framebank_replay.log').open('xb') as log:
    process=subprocess.Popen([sys.executable,'-u','-B',str(root/'board_framebank_replay.py')],stdout=log,stderr=subprocess.STDOUT,cwd=str(root),env=os.environ.copy(),start_new_session=True)
result={'status':'ACTUAL_BOARD_LOWRES_PERIODIC_REPLAY_PROCESS_STARTED','PID':process.pid,'offered_slots_each_size':100,
        'sizes':[192,256,320],'offered_Hz':5,'background_identity_active':False,'camera_active':False,
        'script_sha256':hashlib.sha256((root/'board_framebank_replay.py').read_bytes()).hexdigest()}
with (root/'launch_framebank_replay.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps(result))
PY
