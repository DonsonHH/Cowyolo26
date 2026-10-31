set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028
squeue -j 129981 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129981 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
tail -n 5 "$root/logs/optimizer-129981.out"
cat "$root/logs/optimizer-129981.err"
