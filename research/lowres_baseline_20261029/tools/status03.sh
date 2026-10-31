set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -j 130502 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130502 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS -P
for file in /share/home/renly/projects/idcoo_research_20261026/lowres_baseline_20261029/logs/baseline-v2-130502.out /share/home/renly/projects/idcoo_research_20261026/lowres_baseline_20261029/logs/baseline-v2-130502.err; do
    if [ -f "$file" ]; then tail -n 8 "$file"; fi
done
