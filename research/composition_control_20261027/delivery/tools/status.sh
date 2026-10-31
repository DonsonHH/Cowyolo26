set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/composition_control
for stage in prepare labels preflight train0 train freeze infer collect; do
 if test -f "$ROOT/logs/${stage}_job_id.txt"; then
  job=$(cat "$ROOT/logs/${stage}_job_id.txt")
  sacct -j "$job" -X --format=JobID,JobName%28,State,ExitCode,Elapsed
  if test -f "$ROOT/logs/${stage}-${job}.out"; then tail -c 4000 "$ROOT/logs/${stage}-${job}.out" | tr '\r' '\n' | tail -n2;fi
  if test -f "$ROOT/logs/${stage}-${job}.err"; then tail -c 2000 "$ROOT/logs/${stage}-${job}.err" | tr '\r' '\n' | tail -n4;fi
  if test "$stage" = train0; then
   if test -f "$ROOT/logs/train-${job}_0.err"; then tail -c 1800 "$ROOT/logs/train-${job}_0.err" | tr '\r' '\n' | tail -n4;fi
  fi
 fi
done
find "$ROOT/results/training" -maxdepth 2 -name progress.json -exec cat {} \; 2>/dev/null || true
