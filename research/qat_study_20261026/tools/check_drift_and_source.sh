set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/qat_study
job=$(cat "$ROOT/logs/drift_job_id.txt")
sacct -j "$job" --format=JobID,State,ExitCode,Elapsed
cat "$ROOT/logs/drift-${job}.out"
tail -n12 "$ROOT/logs/drift-${job}.err"
for name in multicam_count_dev multicam_count_finetuned_dev; do cat "/share/home/renly/projects/idcoo_research_20261026/results/$name/summary.json";done
