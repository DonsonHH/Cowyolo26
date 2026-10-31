set -euo pipefail
test "$(id -un)" = root
XILINX_XRT=/usr /usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json, os, subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_workload_ablation_20261031')
assert not (root/'failed_collection_launch_v1.json').exists()
end=json.loads((root/'results/terminal.json').read_text())
assert end['status']=='FAILED' and not (Path('/proc')/str(end['PID'])).exists()
with (root/'failed_collection_v1.log').open('xb') as log:
 child=subprocess.Popen(['/usr/local/share/pynq-venv/bin/python3','-u',str(root/'collect_failed_results_v1.py')],
                        stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
                        env={**os.environ,'XILINX_XRT':'/usr'})
value={'status':'FAILED_ORIGINAL_TASK_COLLECTION_LAUNCHED_ONCE','PID':child.pid,
       'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
(root/'failed_collection_launch_v1.json').write_bytes((json.dumps(value,indent=2)+'\n').encode())
print(json.dumps(value),flush=True)
PY
