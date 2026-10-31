set -euo pipefail
test "$(id -un)" = xilinx
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json
helper=Path('/home/xilinx/jupyter_notebooks/cow_research_access_resume_20261031')
source=Path('/home/xilinx/jupyter_notebooks/cow_research_identity_trigger_pair_20261030')
launch=json.loads((helper/'collector_launch_v1.json').read_text());pid=launch['PID'];proc=Path('/proc')/str(pid)
v={'status':'SAME_RECOVERY_COLLECTOR_READONLY_OBSERVATION','PID':pid,'proc_exists':proc.exists(),
   'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'launch_boot_id':launch['collection_boot_id'],
   'proc_stat':(proc/'stat').read_text()if(proc/'stat').exists()else None,
   'log_tail':(helper/'collector_v1.log').read_text()[-3500:],
   'transfer':json.loads((source/'interruption_recovery_transfer_v1.json').read_text())if(source/'interruption_recovery_transfer_v1.json').is_file()else None,
   'archive_bytes_now':(source/'trigger_pair_interruption_originals_v1.tar.xz').stat().st_size if(source/'trigger_pair_interruption_originals_v1.tar.xz').exists()else None,
   'new_model_forwards':0}
print(json.dumps(v),flush=True)
PY
