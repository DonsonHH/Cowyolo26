set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130565 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026/pynq_rot192_compile_20261029
tail -n 9 logs/compile-130565.out
tail -n 5 logs/compile-130565.err
if test -f results/qualification/summary.json; then cat results/qualification/summary.json; fi
