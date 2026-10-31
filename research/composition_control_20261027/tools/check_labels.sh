set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/composition_control
job=$(cat "$ROOT/logs/labels_job_id.txt")
sacct -j "$job" --format=JobID,State,ExitCode,Elapsed
tail -n3 "$ROOT/logs/labels-${job}.out"
tail -n8 "$ROOT/logs/labels-${job}.err"
