set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130610 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026/pynq_o8_sizes_20261030
tail -n 6 logs/ordered-130610.err
../env/bin/python - <<'PY'
from pathlib import Path
p=Path('results/ordered_reference/summary.json')
if p.exists():
 import json
 s=json.loads(p.read_text());print(json.dumps({k:v for k,v in s.items() if k!='rows'}));print(json.dumps([r for r in s['rows'] if not r['ordered_full_raw_bytes_exact_to_prior_native']]))
PY
