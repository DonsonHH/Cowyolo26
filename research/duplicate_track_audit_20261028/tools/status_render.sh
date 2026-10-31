set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/duplicate_track_audit_20261028
jobid=$(cat "$root/render_job_id.txt")
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j "$jobid" --format=JobID,State,ExitCode,Elapsed,AllocTRES -P
test ! -f "$root/logs/render-$jobid.err" || cat "$root/logs/render-$jobid.err"
test ! -f "$root/logs/render-$jobid.out" || tail -n 1 "$root/logs/render-$jobid.out"
