set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/qat_study
for name in smoke study; do
  if test -f "$ROOT/logs/${name}_job_id.txt"; then
    job=$(cat "$ROOT/logs/${name}_job_id.txt")
    sacct -j "$job" --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS,NodeList
    tail -n 12 "$ROOT/logs/${name}-${job}.out" || true
    tail -n 12 "$ROOT/logs/${name}-${job}.err" || true
  fi
done
if test -f "$ROOT/results/smoke/summary.json"; then cat "$ROOT/results/smoke/summary.json"; fi
