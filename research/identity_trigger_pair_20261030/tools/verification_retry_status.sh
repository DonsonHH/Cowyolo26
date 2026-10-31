set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_trigger_pair_20261030
job_id=$(cat verification_retry_v2_job_id.txt)
squeue -j "$job_id" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sacct -j "$job_id" --format=JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,MaxRSS --parsable2
tail -n 10 "logs/verify-$job_id.out"
tail -n 20 "logs/verify-$job_id.err"
