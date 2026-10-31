set -euo pipefail
stage=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027
squeue -j 129917 -o '%.18i|%.9P|%.25j|%.8T|%.10M|%R'
sacct -j 129917 --format=JobID,JobName%27,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS -P
test ! -f "$stage/logs/smoke-129917.out" || tail -n 5 "$stage/logs/smoke-129917.out"
test ! -s "$stage/logs/smoke-129917.err" || tail -n 18 "$stage/logs/smoke-129917.err"
test ! -f "$stage/results/preflight.json" || cat "$stage/results/preflight.json"
