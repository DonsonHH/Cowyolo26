set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -j 130504 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130504 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS -P
for f in /share/home/renly/projects/idcoo_research_20261026/lowres_baseline_20261029/logs/media-130504.out /share/home/renly/projects/idcoo_research_20261026/lowres_baseline_20261029/logs/media-130504.err; do
 if [ -f "$f" ]; then tail -c 1700 "$f"; fi
done
