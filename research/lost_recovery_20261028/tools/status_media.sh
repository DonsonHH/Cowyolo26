set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/lost_recovery_20261028
jobid=$(cat "$root/media_job_id.txt")
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j "$jobid" --format=JobID,State,ExitCode,Elapsed,AllocTRES -P
test ! -f "$root/logs/media-$jobid.err" || tail -n 20 "$root/logs/media-$jobid.err"
test ! -f "$root/logs/media-$jobid.out" || tail -n 3 "$root/logs/media-$jobid.out"
