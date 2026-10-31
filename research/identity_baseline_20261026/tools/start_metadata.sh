set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/identity_baseline
mkdir -p "$ROOT/logs" "$ROOT/models"
test ! -e "$ROOT/logs/metadata_pid.txt"
nohup /share/home/renly/miniconda3/bin/python "$ROOT/tools/inspect_multicam_metadata.py" > "$ROOT/logs/metadata.out" 2> "$ROOT/logs/metadata.err" < /dev/null &
echo "$!" | tee "$ROOT/logs/metadata_pid.txt"
