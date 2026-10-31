set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -j 130498 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130498 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS -P
for f in /share/home/renly/projects/idcoo_research_20261026/detector_torso_pairs_20261029/logs/pairs-130498.out /share/home/renly/projects/idcoo_research_20261026/detector_torso_pairs_20261029/logs/pairs-130498.err; do
    if [ -f "$f" ]; then tail -n 9 "$f"; fi
done
