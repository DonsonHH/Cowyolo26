set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/source_demo
job=$(cat "$ROOT/logs/preview_job_id.txt")
sacct -j "$job" --format=JobID,State,ExitCode,Elapsed,MaxRSS
cat "$ROOT/logs/preview-${job}.out"
tail -n12 "$ROOT/logs/preview-${job}.err"
find "$ROOT/results/preview" -maxdepth 1 -type f -printf '%s %f\n'
