set -euo pipefail
stage=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027
squeue -j 129918 -o '%.18i|%.9P|%.25j|%.8T|%.10M|%R'
sacct -j 129918 --format=JobID,JobName%27,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS -P
test ! -f "$stage/results/training/progress.json" || cat "$stage/results/training/progress.json"
test ! -f "$stage/results/training/summary.json" || cat "$stage/results/training/summary.json"
test ! -f "$stage/logs/train-129918.out" || tail -n 4 "$stage/logs/train-129918.out" | cut -c 1-1800
test ! -s "$stage/logs/train-129918.err" || tail -n 18 "$stage/logs/train-129918.err" | cut -c 1-1800
