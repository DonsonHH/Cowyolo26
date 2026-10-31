set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -j 130516 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130516 --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS -P
for file in /share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029/logs/preflight-130516.out /share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029/logs/preflight-130516.err; do
    if [ -f "$file" ]; then tail -n 12 "$file"; fi
done
