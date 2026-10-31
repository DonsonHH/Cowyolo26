set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export PYTHONDONTWRITEBYTECODE=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,os,sys,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_validation_v2_20261029')
assert hashlib.sha256((root/'protocol.json').read_bytes()).hexdigest()=='b48985eeb6bb90bb9dbe5d75346d3a8253d291e83e8bffbabd410b7bdc5db213'
assert hashlib.sha256((root/'board_profile.py').read_bytes()).hexdigest()=='48b714cbcb9d32cd026738282d0fd00bfd27dcd8758cdf64e83d58d4dc254ece'
assert not (root/'probe192').exists() and not (root/'launch_probe192.json').exists()
assert not Path('/proc/8082').exists()
with (root/'probe192.log').open('xb') as log:
    child=subprocess.Popen([sys.executable,'-u','-B',str(root/'board_profile.py'),'--size','192','--run','probe192','--probe'],
          stdout=log,stderr=subprocess.STDOUT,cwd=str(root),env=os.environ.copy(),start_new_session=True)
record={'status':'SINGLE_SAMPLE_PROBE_STARTED','PID':child.pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'new_overlay_action_authorized_for_this_probe':True,'formal_samples':0,'probe_samples_expected':1}
with (root/'launch_probe192.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps(record))
PY
