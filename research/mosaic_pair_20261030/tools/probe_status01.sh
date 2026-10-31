set -euo pipefail
sacct -j 130629 -X --format=JobID,State,ExitCode,Elapsed -P
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import json
root=Path('/share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030')
p=root/'results/regression_diagnostic.json'
if p.exists():
 s=json.loads(p.read_text());print(json.dumps({'rows':[dict(scene=r['scene'],seed=r['seed'],stride=r['stride'],counts=r['difference_counts'],maxima=r['maximum_errors'],confirmed_exact=r['confirmed_events_exact'],handoff_exact=r['handoff_events_exact'],first_diff=r['first12_differences'][:1]) for r in s['rows']]},indent=2))
else:
 print((root/'logs/regression-probe-130629.err').read_text())
PY
