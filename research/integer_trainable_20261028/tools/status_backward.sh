set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_trainable_20261028
squeue -j 129990 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129989,129990 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/backward-129990.err" || tail -n 10 "$root/logs/backward-129990.err"
if test -f "$root/results/backward_probe/summary.json"; then
  /share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import json
p=Path('/share/home/renly/projects/idcoo_research_20261026/integer_trainable_20261028/results/backward_probe/summary.json')
d=json.loads(p.read_text())
for r in d['conditions']:
    print(json.dumps({'condition':r['condition'],'parameters':r['parameter_tensors'],
          'missing':len(r['missing_gradient_tensors']),'frozen':len(r['frozen_parameter_tensors']),
          'nonfinite':len(r['nonfinite_gradient_tensors']), 'missing_equals_frozen':r['missing_gradient_tensors']==r['frozen_parameter_tensors'],
          'first_missing':r['missing_gradient_tensors'][:3], 'finite_nonzero':r['finite_nonzero_gradient_tensors']}))
PY
fi
