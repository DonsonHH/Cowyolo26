set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130566 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026/pynq_frontend_port_20261029
tail -n 9 logs/regression-130566.out
tail -n 12 logs/regression-130566.err
if test -f results/regression/summary.json; then head -n 16 results/regression/summary.json; fi
