ROOT=/share/home/renly/projects/idcoo_research_20261026
sacct -j 129664 --format=JobID,State,ExitCode,Elapsed -n
python - <<'PY'
from pathlib import Path
root=Path('/share/home/renly/projects/idcoo_research_20261026')
p=root/'logs/pilot-replay-129664.out'
if p.exists():
 rows=[s for s in p.read_text().splitlines() if s.startswith('{')]
 print('\n'.join(rows[-5:]))
p=root/'logs/pilot-replay-129664.err'
if p.exists():print(p.read_text()[-900:])
PY
