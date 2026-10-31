set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/activation_range_20261028
squeue -j 130003 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 130003 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/probe-130003.out" || tail -n 5 "$root/logs/probe-130003.out"
test ! -f "$root/logs/probe-130003.err" || tail -n 12 "$root/logs/probe-130003.err"
