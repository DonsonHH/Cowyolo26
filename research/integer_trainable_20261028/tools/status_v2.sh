set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_trainable_20261028
squeue -j 129991 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129989,129990,129991 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/smoke-v2-129991.out" || tail -n 8 "$root/logs/smoke-v2-129991.out"
test ! -f "$root/logs/smoke-v2-129991.err" || tail -n 8 "$root/logs/smoke-v2-129991.err"
