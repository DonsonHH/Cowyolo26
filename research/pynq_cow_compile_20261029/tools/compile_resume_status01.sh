set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -j 130539 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130539 --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS -P
for file in /share/home/renly/projects/idcoo_research_20261026/pynq_cow_compile_20261029/logs/compile-130539.out /share/home/renly/projects/idcoo_research_20261026/pynq_cow_compile_20261029/logs/compile-130539.err; do
    if [ -f "$file" ]; then tail -n 18 "$file"; fi
done
