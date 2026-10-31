set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028
jobid=$(cat "$root/compact_job_id.txt")
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j "$jobid" --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/compact-$jobid.err" || cat "$root/logs/compact-$jobid.err"
if test "$(sacct -j "$jobid" -X -n -o State | xargs)" = COMPLETED; then cat "$root/results/compact_delivery_record.json"; fi
