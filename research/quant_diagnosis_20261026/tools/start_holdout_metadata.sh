set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/quant_diagnosis
test ! -e "$ROOT/logs/holdout_metadata_pid.txt"
nohup /share/home/renly/miniconda3/bin/python "$ROOT/tools/stage_holdout_metadata.py" > "$ROOT/logs/holdout_metadata.out" 2> "$ROOT/logs/holdout_metadata.err" < /dev/null &
echo "$!" | tee "$ROOT/logs/holdout_metadata_pid.txt"
