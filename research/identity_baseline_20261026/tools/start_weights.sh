set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/identity_baseline
mkdir -p "$ROOT/logs"
test ! -e "$ROOT/logs/weights_pid.txt"
nohup /share/home/renly/miniconda3/bin/python "$ROOT/tools/stage_mobilenet.py" > "$ROOT/logs/weights.out" 2> "$ROOT/logs/weights.err" < /dev/null &
echo "$!" | tee "$ROOT/logs/weights_pid.txt"
