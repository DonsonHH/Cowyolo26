set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130506 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS -P
for file in /share/home/renly/projects/idcoo_research_20261026/lowres_roi_20261029/logs/pairs-130506.out /share/home/renly/projects/idcoo_research_20261026/lowres_roi_20261029/logs/pairs-130506.err; do
    if [ -f "$file" ]; then tail -n 12 "$file"; fi
done
find /share/home/renly/projects/idcoo_research_20261026/lowres_roi_20261029/results -maxdepth 2 -type f -printf '%s %p\n' | sort
