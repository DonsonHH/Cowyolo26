set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -j 130559 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130559 --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS -P
for file in /share/home/renly/projects/idcoo_research_20261026/factorial_lane_crop_20261029/logs/crop-130559.out /share/home/renly/projects/idcoo_research_20261026/factorial_lane_crop_20261029/logs/crop-130559.err; do
    if [ -f "$file" ]; then tail -n 6 "$file"; fi
done
