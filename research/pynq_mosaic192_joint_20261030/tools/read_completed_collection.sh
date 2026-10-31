set -euo pipefail
test "$(id -un)" = root
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib
root=Path('/home/xilinx/jupyter_notebooks/cow_research_mosaic192_joint_20261030')
assert not (Path('/proc')/'31517').exists(),'Original archive process remains live; do not restart'
meta=json.loads((root/'transfer.json').read_text());a=Path(meta['archive'])
assert a.stat().st_size==meta['bytes'] and hashlib.sha256(a.read_bytes()).hexdigest()==meta['sha256']
s=json.loads((root/'results/record.json').read_text())
print(json.dumps({'transfer':meta,'archive_PID':31517,'archive_PID_absent':True,'cases':s['cases'],
 'model_status':s['status'],'new_model_forwards':0,'new_archive_created':False}))
PY
