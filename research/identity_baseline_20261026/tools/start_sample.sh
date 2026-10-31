set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/identity_baseline
test -s "$ROOT/protocol/identity_pilot_v1.json"
test ! -e "$ROOT/logs/sample_pid.txt"
nohup /share/home/renly/miniconda3/bin/python "$ROOT/tools/stage_identity_sample.py" > "$ROOT/logs/sample.out" 2> "$ROOT/logs/sample.err" < /dev/null &
echo "$!" | tee "$ROOT/logs/sample_pid.txt"
