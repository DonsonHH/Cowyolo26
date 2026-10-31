set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/tracker_clock_20261028
jobid=$(cat "$root/verify_job_id.txt")
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j "$jobid" --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/verify-$jobid.err" || cat "$root/logs/verify-$jobid.err"
if test "$(sacct -j "$jobid" -X -n -o State | xargs)" = COMPLETED; then
  cat "$root/results/delivery_record.json"
  tail -n 2 "$root/logs/verify-$jobid.out"
fi
