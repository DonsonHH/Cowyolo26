set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028
squeue -j 129975 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129975 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
tail -n 5 "$root/logs/reference-129975.out"
cat "$root/logs/reference-129975.err"
find "$root/results" -maxdepth 2 -type f -printf '%s %P\n'
