set -euo pipefail
squeue -j 130622 -o '%.20i|%.9P|%.28j|%.8T|%.10M|%R'
sacct -j 130622 -X --format=JobID,State,ExitCode,Elapsed -P
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import json
r=Path('/share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030')
p=json.loads((r/'protocol/training_v1.json').read_text())
for c in p['conditions']:
 f=r/'results/training'/c['name']/'progress.json'
 print(c['name'],f.read_text() if f.exists() else 'NOT_STARTED_OR_BEFORE_FIRST_EPOCH')
for f in sorted((r/'logs').glob('train-130622_*.err')):
 text=f.read_text()
 if text.strip():print(f.name,text[-1200:])
PY
