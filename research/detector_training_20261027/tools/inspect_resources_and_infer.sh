set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/detector_training
sacct -j 129785 --format=JobID,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS,MaxVMSize,AllocTRES%80
job=$(cat "$ROOT/logs/infer_job_id.txt")
sacct -j "$job" -X --format=JobID,State,ExitCode,Elapsed
if test -f "$ROOT/logs/infer-${job}.out"; then tail -n4 "$ROOT/logs/infer-${job}.out";fi
if test -f "$ROOT/logs/infer-${job}.err"; then tail -n4 "$ROOT/logs/infer-${job}.err";fi
