set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_qat_20261028
jobid=$(cat "$root/verify_job_id.txt")
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j "129998,$jobid" --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/check-$jobid.err" || cat "$root/logs/check-$jobid.err"
if test -f "$root/results/independent_verification.json"; then cat "$root/results/independent_verification.json"; fi
