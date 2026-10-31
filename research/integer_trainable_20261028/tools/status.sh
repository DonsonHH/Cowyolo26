set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_trainable_20261028
squeue -j 129989 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129989 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/smoke-129989.out" || tail -n 8 "$root/logs/smoke-129989.out"
test ! -f "$root/logs/smoke-129989.err" || tail -n 15 "$root/logs/smoke-129989.err"
