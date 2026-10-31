set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028
jobid=$(cat "$root/verify_job_id.txt")
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j "130215,130217,$jobid" --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/verify-$jobid.err" || cat "$root/logs/verify-$jobid.err"
if test -f "$root/results/independent_verification.json"; then cat "$root/results/independent_verification.json"; fi
