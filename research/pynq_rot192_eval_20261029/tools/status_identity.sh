set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130569 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026/pynq_identity_ncnn_20261029
tail -n 10 logs/export-130569.out
tail -n 12 logs/export-130569.err
if test -f results/export/summary.json; then cat results/export/summary.json; fi
