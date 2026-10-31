set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -j 130503 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130501,130502,130503 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS -P
for f in /share/home/renly/projects/idcoo_research_20261026/lowres_baseline_20261029/logs/toros-130503.out /share/home/renly/projects/idcoo_research_20261026/lowres_baseline_20261029/logs/toros-130503.err; do
 if [ -f "$f" ]; then tail -n 5 "$f"; fi
done
