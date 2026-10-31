set -euo pipefail
test "$(id -un)" = root
XILINX_XRT=/usr /usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,os,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_parent_only_workload_20261031')
assert not(root/'collection_launch.json').exists()and not(root/'final_state.json').exists()
end=json.loads((root/'results/terminal.json').read_text());assert end['status']=='ALL8_WORKLOAD_2X2_MIRROR_ORDER_REPEATS_COMPLETE'
assert not(Path('/proc')/str(end['PID'])).exists()
with(root/'collection.log').open('xb')as log:
 child=subprocess.Popen(['/usr/local/share/pynq-venv/bin/python3','-u',str(root/'collect_results.py')],stdin=subprocess.DEVNULL,
                        stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env={**os.environ,'XILINX_XRT':'/usr'})
value={'status':'WORKLOAD_COLLECTION_LAUNCHED_ONCE','PID':child.pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
(root/'collection_launch.json').write_bytes((json.dumps(value,indent=2)+'\n').encode());print(json.dumps(value),flush=True)
PY
