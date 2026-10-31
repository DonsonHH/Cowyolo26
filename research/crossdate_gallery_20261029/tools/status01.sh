set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -j 130422 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130422 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS -P
for f in /share/home/renly/projects/idcoo_research_20261026/crossdate_gallery_20261029/logs/study-130422.out /share/home/renly/projects/idcoo_research_20261026/crossdate_gallery_20261029/logs/study-130422.err; do
    if [ -f "$f" ]; then cat "$f"; fi
done
