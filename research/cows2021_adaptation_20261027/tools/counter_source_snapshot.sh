set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json
root=Path('/share/home/renly/projects/idcoo_research_20261026')
rows=[]
for name in ['zone_counter.py','event_metrics.py']:
    p=root/'phase2/tools'/name
    rows.append({'path':str(p),'file_name':name,'bytes':p.stat().st_size,
                 'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':p.read_text()})
print(json.dumps(rows),flush=True)
PY
