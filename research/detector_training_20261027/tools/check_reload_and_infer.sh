set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/detector_training
job=$(cat "$ROOT/logs/reload_job_id.txt")
sacct -j "$job" --format=JobID,State,ExitCode,Elapsed,MaxRSS
cat "$ROOT/logs/reload-${job}.out"
cat "$ROOT/logs/reload-${job}.err"
infer=$(cat "$ROOT/logs/infer_job_id.txt")
sacct -j "$infer" -X --format=JobID,State,ExitCode,Elapsed
tail -n4 "$ROOT/logs/infer-${infer}.out"
tail -n8 "$ROOT/logs/infer-${infer}.err"
