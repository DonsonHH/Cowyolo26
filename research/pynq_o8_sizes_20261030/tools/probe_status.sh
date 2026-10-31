set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130606 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026/pynq_o8_sizes_20261030
tail -n 6 logs/probe-130606.err
../env/bin/python - <<'PY'
from pathlib import Path
import json
p=Path('results/probe320/summary.json')
if p.exists():
 s=json.loads(p.read_text());print(json.dumps({'status':s['status'],'actual_forwards':s['actual_network_forwards'],
  'controls':[{'options':c['options'],'complete_raw_exact':c['complete_raw_exact_to_reference'],
   'first_differences':c['boundary_differences'][:5],'unavailable':len(c['unavailable_boundaries'])} for c in s['controls']]}))
PY
