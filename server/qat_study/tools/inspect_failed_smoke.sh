set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/qat_study
cat "$ROOT/logs/smoke-129738.err"
find "$ROOT/results/smoke" -maxdepth 1 -type f -printf "%s %p\n"
