set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130542 --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS -P
for file in /share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029/logs/recover-130542.out /share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029/logs/recover-130542.err; do
    if [ -f "$file" ]; then tail -n 12 "$file"; fi
done
