set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/phase3_diagnosis
sacct -j 129691,129692,129693 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sha256sum "$ROOT/tools/capture_raw_and_tracked.py" "$ROOT/tools/diagnose_layers.py" "$ROOT/annotations/diagnosis_protocol_v1.json"
wc -c "$ROOT/logs/capture-129692.err" "$ROOT/logs/layers-129693.err"
test "$(sacct -j 129692 -X --format=State --noheader | tr -d ' ')" = COMPLETED
test "$(sacct -j 129693 -X --format=State --noheader | tr -d ' ')" = COMPLETED
test -s "$ROOT/results/capture/summary.json"
test -s "$ROOT/results/layers/diagnostic_summary.json"
