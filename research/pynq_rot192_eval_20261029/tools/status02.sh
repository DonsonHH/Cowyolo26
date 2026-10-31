set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130568 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026/pynq_rot192_eval_20261029
tail -n 10 logs/quality-130568.out
tail -n 8 logs/quality-130568.err
if test -f results/quality_v2/summary.json; then head -n 28 results/quality_v2/summary.json; fi
