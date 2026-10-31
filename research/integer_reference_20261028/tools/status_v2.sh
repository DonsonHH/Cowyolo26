set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028
jobid=$(cat "$root/job_id_v2.txt")
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j "129975,$jobid" --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
test ! -e "$root/logs/reference-$jobid.out" || tail -n 4 "$root/logs/reference-$jobid.out"
test ! -e "$root/logs/reference-$jobid.err" || cat "$root/logs/reference-$jobid.err"
test ! -d "$root/results" || find "$root/results" -maxdepth 2 -type f -printf '%s %P\n'
