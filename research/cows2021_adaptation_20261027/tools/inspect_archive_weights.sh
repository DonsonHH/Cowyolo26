set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import json,hashlib
root=Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
directory=root/'results/archive_index_probe/entries.json'
rows=json.loads(directory.read_text())
weights=[r for r in rows if not r['directory'] and ('/3Weights/' in r['name'] or ('weight' in r['name'].lower() and r['name'].endswith(('.pt','.pth','.h5','.pkl','.onnx'))))]
result={'status':'OFFICIAL_ZIP_WEIGHT_MEMBERS_LISTED_METADATA_ONLY',
        'source_entries_sha256':hashlib.sha256(directory.read_bytes()).hexdigest(),
        'weights_count':len(weights),'members':weights,
        'weight_payload_downloaded_or_loaded':False,'new_model_forward_or_training':False}
target=root/'results/archive_weight_members.json';assert not target.exists()
target.write_text(json.dumps(result,indent=2))
print(json.dumps(result),flush=True)
PY
ps -p 2794954 -o pid,lstart,etime,state,args
stage="$project/cows2021_adaptation_20261027"
test ! -f "$stage/results/download_attempt_01/progress.json" || cat "$stage/results/download_attempt_01/progress.json"
