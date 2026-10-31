set -euo pipefail
test "$(id -un)" = xilinx
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,subprocess
helper=Path('/home/xilinx/jupyter_notebooks/cow_research_access_resume_20261031')
source=Path('/home/xilinx/jupyter_notebooks/cow_research_identity_trigger_pair_20261030')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='e7059099-ecb8-451e-a9aa-a66c8222196b'
script=helper/'collect_after_interruption_v1.py'
assert hashlib.sha256(script.read_bytes()).hexdigest()=='cadd67974aa2b1356ff229a1b986e5e164cc1e95f79c3feeec837dbfafb5c494'
assert hashlib.sha256((source/'run_protocol.json').read_bytes()).hexdigest()=='4217824d2964e56218c566a73096a2f282c94020f3176c74bf86cef9a270513c'
assert not(source/'interruption_recovery_v1.json').exists()
assert not(source/'trigger_pair_interruption_originals_v1.tar.xz').exists()
launch=helper/'collector_launch_v1.json';assert not launch.exists()
log=helper/'collector_v1.log'
with log.open('xb')as f:
 process=subprocess.Popen(['/usr/local/share/pynq-venv/bin/python3','-u',str(script)],stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
record={'status':'ORIGINAL_RESULT_COLLECTION_LAUNCHED_ONCE_NO_MODEL_OR_PL_LOAD','created_untrusted_board_UTC':datetime.now(timezone.utc).isoformat(),
        'PID':process.pid,'collection_boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'script_sha256':hashlib.sha256(script.read_bytes()).hexdigest(),'log_file':str(log),'new_model_forwards':0,'source_experiment_restarted':False}
launch.write_bytes(json.dumps(record,indent=2).encode()+bytes([10]));print(json.dumps(record),flush=True)
PY
