set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/detector_training
for stage in train infer collect; do
  if test -f "$ROOT/logs/${stage}_job_id.txt"; then
    job=$(cat "$ROOT/logs/${stage}_job_id.txt")
    sacct -j "$job" --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS
    if test -f "$ROOT/logs/${stage}-${job}.out"; then tail -c 16000 "$ROOT/logs/${stage}-${job}.out" | tr '\r' '\n' | tail -n4; fi
    if test -f "$ROOT/logs/${stage}-${job}.err"; then tail -c 3000 "$ROOT/logs/${stage}-${job}.err" | tr '\r' '\n' | tail -n4; fi
  fi
done
find "$ROOT/results/training" -maxdepth 2 -name results.csv -exec sh -c 'echo "$1"; tail -n2 "$1"' _ {} \; 2>/dev/null || true
