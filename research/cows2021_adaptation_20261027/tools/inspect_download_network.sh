set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
stage="$project/cows2021_adaptation_20261027"
ps -p 2794954 -o pid,lstart,etime,state,args
test ! -f "$stage/results/download_attempt_01/progress.json" || cat "$stage/results/download_attempt_01/progress.json"
tail -n 3 "$stage/logs/download-attempt-01.log"
ss -ltn '( sport = :2080 or sport = :27831 )'
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import json
stage=Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
files=list((stage/'raw_images').rglob('*.jpg'))
print(json.dumps({'saved_images':len(files),'bytes':sum(p.stat().st_size for p in files)}))
PY
