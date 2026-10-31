set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_qat_20261028
squeue -j 129998 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129998 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/train-129998.out" || tail -n 8 "$root/logs/train-129998.out"
test ! -f "$root/logs/train-129998.err" || tail -n 12 "$root/logs/train-129998.err"
