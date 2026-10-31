set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/source_demo
job=$(cat "$ROOT/logs/collection_job_id.txt")
sacct -j "$job" --format=JobID,State,ExitCode,Elapsed,MaxRSS
cat "/share/home/renly/projects/idcoo_research_20261026/results/preview-qat-collect-${job}.out"
tail -n12 "/share/home/renly/projects/idcoo_research_20261026/results/preview-qat-collect-${job}.err"
for stage in qat_study source_demo; do cat "/share/home/renly/projects/idcoo_research_20261026/$stage/delivery_bundle.json";done
