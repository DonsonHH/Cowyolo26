set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_final20_20261030
job_id=$(cat evaluation_job_id.txt)
sacct -j "$job_id" --format=JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,MaxRSS --parsable2
squeue -j "$job_id" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
if test -f results/evaluation/summary.json; then cat results/evaluation/summary.json; fi
