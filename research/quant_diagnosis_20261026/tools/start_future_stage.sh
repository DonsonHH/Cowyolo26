set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/quant_diagnosis
test -s "$ROOT/protocol/future_comparison_frozen.json"
test ! -e "$ROOT/logs/future_stage_pid.txt"
nohup /share/home/renly/miniconda3/bin/python "$ROOT/tools/stage_reserved_images.py" > "$ROOT/logs/future_stage.out" 2> "$ROOT/logs/future_stage.err" < /dev/null &
echo "$!" | tee "$ROOT/logs/future_stage_pid.txt"
