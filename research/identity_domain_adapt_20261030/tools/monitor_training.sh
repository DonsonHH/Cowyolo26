set -euo pipefail
squeue -j 130777 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sacct -j 130777 --format=JobID,JobName%24,State,ExitCode,Elapsed,AllocCPUS,MaxRSS -P
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import json
r=Path('/share/home/renly/projects/idcoo_research_20261026/identity_domain_adapt_20261030')
for index in range(6):
 f=r/'logs'/('train-130777_'+str(index)+'.out');e=f.with_suffix('.err')
 if f.exists():print(json.dumps({'index':index,'stdout_tail':f.read_text()[-700:],'stderr_tail':e.read_text()[-1000:] if e.exists()else None}))
PY
