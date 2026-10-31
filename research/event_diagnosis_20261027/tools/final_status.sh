set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/event_diagnosis
for stage in capture layers source collect; do job=$(cat "$ROOT/logs/${stage}_job_id.txt"); sacct -j "$job" --format=JobID,State,ExitCode,Elapsed,MaxRSS,NodeList;done
if test -f "$ROOT/delivery_bundle.json"; then cat "$ROOT/delivery_bundle.json";fi
