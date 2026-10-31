set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130609 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026/pynq_o8_sizes_20261030
tail -n 6 logs/causal-130609.err
../env/bin/python - <<'PY'
from pathlib import Path
p=Path('results/probe320_causal/summary.json')
if p.exists():print(p.read_text())
PY
