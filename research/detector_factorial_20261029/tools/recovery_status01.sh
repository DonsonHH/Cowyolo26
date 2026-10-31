set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -j 130518,130537 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130537 --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS -P
for file in /share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029/logs/recover-130537.out /share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029/logs/recover-130537.err; do
    if [ -f "$file" ]; then tail -n 10 "$file"; fi
done
