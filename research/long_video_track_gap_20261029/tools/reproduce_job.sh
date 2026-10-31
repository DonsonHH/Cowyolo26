#!/usr/bin/env bash
set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
ROOT="$PROJECT/long_video_track_gap_20261029"
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 HF_HUB_OFFLINE=1
"$PROJECT/env/bin/python" "$ROOT/tools/reproduce.py"
set +e
"$PROJECT/env/bin/python" "$ROOT/tools/reproduce.py" --signal > "$ROOT/results/reproduce/red_signal_1.json"
first=$?
"$PROJECT/env/bin/python" "$ROOT/tools/reproduce.py" --signal > "$ROOT/results/reproduce/red_signal_2.json"
second=$?
set -e
test "$first" = 1
test "$second" = 1
cat "$ROOT/results/reproduce/red_signal_1.json"
printf 'EXPECTED_SIGNAL_EXIT_CODES=%s,%s\n' "$first" "$second"
