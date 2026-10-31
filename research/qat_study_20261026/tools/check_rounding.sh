set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/qat_study
job=$(cat "$ROOT/logs/rounding_job_id.txt")
sacct -j "$job" --format=JobID,State,ExitCode,Elapsed,MaxRSS
cat "$ROOT/logs/rounding-${job}.out"
tail -n20 "$ROOT/logs/rounding-${job}.err"
