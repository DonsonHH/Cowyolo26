set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_final20_20261030
job_id=$(cat figure_job_id.txt)
sacct -j "$job_id" --format=JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,MaxRSS --parsable2
if test -f results/figure_manifest.json; then cat results/figure_manifest.json; fi
