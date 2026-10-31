set -euo pipefail
squeue -j 130617,130618 -o '%.18i|%.9P|%.28j|%.8T|%.10M|%R'
sacct -j 130617,130618 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import json
root=Path('/share/home/renly/projects/idcoo_research_20261026/training_coverage_20261030')
p=root/'results/audit/summary.json'
if p.exists():
 s=json.loads(p.read_text());print(json.dumps({k:v for k,v in s.items() if k!='by_date'},indent=2))
for name in ['audit-130617.err','media-130618.out','media-130618.err']:
 f=root/'logs'/name
 if f.exists():print(name+':'+f.read_text()[-1500:])
PY
