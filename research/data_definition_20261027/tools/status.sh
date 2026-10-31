set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/data_definition
for stage in audit collect; do if test -f "$ROOT/logs/${stage}_job_id.txt"; then job=$(cat "$ROOT/logs/${stage}_job_id.txt");sacct -j "$job" --format=JobID,State,ExitCode,Elapsed,MaxRSS; if test -f "$ROOT/logs/${stage}-${job}.out"; then tail -n2 "$ROOT/logs/${stage}-${job}.out";fi; if test -f "$ROOT/logs/${stage}-${job}.err"; then tail -n8 "$ROOT/logs/${stage}-${job}.err";fi;fi;done
if test -f "$ROOT/delivery_bundle.json"; then cat "$ROOT/delivery_bundle.json";fi
