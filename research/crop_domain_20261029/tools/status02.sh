set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -j 130496 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130496 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS -P
for f in /share/home/renly/projects/idcoo_research_20261026/crop_domain_20261029/logs/study-130496.out /share/home/renly/projects/idcoo_research_20261026/crop_domain_20261029/logs/study-130496.err; do
    if [ -f "$f" ]; then cat "$f"; fi
done
