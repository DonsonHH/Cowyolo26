set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/quant_diagnosis
job=$(cat "$ROOT/logs/future_job_id.txt")
sacct -j "$job" -P --format=JobID,JobName,State,ExitCode,Elapsed
tail -n 12 "$ROOT/logs/future-$job.out"
tail -n 6 "$ROOT/logs/future-$job.err"
