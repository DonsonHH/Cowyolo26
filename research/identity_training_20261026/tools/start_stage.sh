set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/identity_training
mkdir -p "$ROOT/logs"
test ! -e "$ROOT/logs/stage_pid.txt"
nohup /share/home/renly/miniconda3/bin/python "$ROOT/tools/stage_training_sample.py" > "$ROOT/logs/stage.out" 2> "$ROOT/logs/stage.err" < /dev/null &
echo "$!" | tee "$ROOT/logs/stage_pid.txt"
