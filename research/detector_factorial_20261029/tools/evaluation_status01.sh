set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -j 130544 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130544 --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS -P
for file in /share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029/logs/evaluate-130544.out /share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029/logs/evaluate-130544.err; do
    if [ -f "$file" ]; then tail -n 8 "$file"; fi
done
