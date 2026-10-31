set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/lost_recovery_20261028
jobid=$(cat "$root/red_job_id.txt")
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j "$jobid" --format=JobID,State,ExitCode,Elapsed,AllocTRES -P
test ! -f "$root/logs/red-$jobid.err" || cat "$root/logs/red-$jobid.err"
test ! -f "$root/results/baseline_red_tests.json" || cat "$root/results/baseline_red_tests.json"
