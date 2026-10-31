set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028
jobid=$(cat "$root/job_id.txt")
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j "$jobid" --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/replay-$jobid.out" || tail -n 3 "$root/logs/replay-$jobid.out"
test ! -f "$root/logs/replay-$jobid.err" || tail -n 10 "$root/logs/replay-$jobid.err"
