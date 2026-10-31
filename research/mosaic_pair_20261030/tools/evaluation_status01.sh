set -euo pipefail
squeue -j 130628 -o '%.18i|%.9P|%.28j|%.8T|%.10M|%R'
sacct -j 130628 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import json
root=Path('/share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030')
for index,name in [(3,'mosaic050_seed27'),(4,'mosaic100_seed28')]:
 log=root/'logs'/('train-130622_'+str(index)+'.err');complete=root/'results/training'/name/'condition_complete.json'
 print(json.dumps({'condition':name,'error_text':log.read_text(),'error_mtime_ns':log.stat().st_mtime_ns,'complete_mtime_ns':complete.stat().st_mtime_ns,'complete_exists':complete.exists()}))
for name in ['evaluation-130628.out','evaluation-130628.err']:
 f=root/'logs'/name
 if f.exists():print(name+':'+f.read_text()[-2000:])
PY
