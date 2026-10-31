set -euo pipefail
stage=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027
squeue -j 129916 -o '%.18i|%.9P|%.25j|%.8T|%.10M|%R'
sacct -j 129916 --format=JobID,JobName%27,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS -P
test ! -f "$stage/logs/labels-129916.out" || tail -n 5 "$stage/logs/labels-129916.out"
test ! -s "$stage/logs/labels-129916.err" || tail -n 14 "$stage/logs/labels-129916.err"
test ! -f "$stage/results/labels_v1/summary.json" || cat "$stage/results/labels_v1/summary.json"
