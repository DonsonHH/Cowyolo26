set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/external_method_regression_20261028
jobid=$(cat "$root/case_job_id.txt")
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j "$jobid" --format=JobID,State,ExitCode,Elapsed,AllocTRES -P
test ! -f "$root/logs/case-$jobid.err" || cat "$root/logs/case-$jobid.err"
test ! -f "$root/logs/case-$jobid.out" || tail -n 1 "$root/logs/case-$jobid.out"
