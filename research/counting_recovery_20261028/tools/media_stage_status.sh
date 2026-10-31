set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028
find "$root/media_runtime_wheels" -maxdepth 1 -type f -printf '%s %f\n'
test ! -f "$root/results/media_runtime_staging.json" || cat "$root/results/media_runtime_staging.json"
ss -ltn '( sport = :2080 )'
