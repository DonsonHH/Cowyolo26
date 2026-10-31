set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/identity_baseline
/share/home/renly/miniconda3/bin/python - <<'PY'
from pathlib import Path
import json
root=Path('/share/home/renly/projects/idcoo_research_20261026/identity_baseline')
audit=json.loads((root/'results/image_audit/summary.json').read_text())
print(json.dumps({'audit':{k:v for k,v in audit.items() if k not in ['near_same_identity_cross_day_candidates']},'near_candidates':len(audit['near_same_identity_cross_day_candidates'])},indent=2))
x=json.loads((root/'results/embedding_baseline/summary.json').read_text())
for key in ['calibration','evaluation']:x[key]={k:v for k,v in x[key].items() if k!='per_identity'}
print(json.dumps(x,indent=2))
x=json.loads((root/'results/group_aggregation/summary.json').read_text())
for condition in x['conditions']:
    for key in ['calibration','evaluation']:condition[key]={k:v for k,v in condition[key].items() if k!='per_identity'}
print(json.dumps(x,indent=2))
PY
