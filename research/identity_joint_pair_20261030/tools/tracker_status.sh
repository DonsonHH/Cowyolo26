set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_joint_pair_20261030
job=$(cat tracker_job_id.txt)
sacct -j "$job" --format=JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,MaxRSS --parsable2
squeue -j "$job" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
if test -f results/tracker_replay/summary.json; then cat results/tracker_replay/summary.json; fi
