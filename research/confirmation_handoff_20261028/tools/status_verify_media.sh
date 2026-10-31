set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/confirmation_handoff_20261028
jobid=$(cat "$root/verify_media_job_id.txt")
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j "$jobid" --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/verify_media-$jobid.err" || tail -n 20 "$root/logs/verify_media-$jobid.err"
test ! -f "$root/logs/verify_media-$jobid.out" || tail -n 3 "$root/logs/verify_media-$jobid.out"
if test "$(sacct -j "$jobid" -X -n -o State | xargs)" = COMPLETED; then cat "$root/results/delivery_record.json"; fi
