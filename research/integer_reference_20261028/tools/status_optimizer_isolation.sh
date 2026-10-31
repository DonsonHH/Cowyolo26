set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028
squeue -j 129982 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129981,129982 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/optimizer-add-129982.err" || cat "$root/logs/optimizer-add-129982.err"
if test -f "$root/results/optimizer_isolation/summary.json"; then
  /share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
import json
from pathlib import Path
folder=Path('/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028/results/optimizer_isolation')
print((folder/'summary.json').read_text())
for row in json.loads((folder/'records.json').read_text()):
    if row['isolated_output_different_elements']: print(json.dumps(row))
PY
fi
