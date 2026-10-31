set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028
squeue -j 129977 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129975,129976,129977 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
test ! -e "$root/logs/check-129977.err" || cat "$root/logs/check-129977.err"
if test -f "$root/results/independent_verification.json"; then
  /share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
import json
from pathlib import Path
p=Path('/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028/results/independent_verification.json')
d=json.loads(p.read_text());print(json.dumps({k:v for k,v in d.items() if k!='candidate_metric_conditions'}))
PY
fi
