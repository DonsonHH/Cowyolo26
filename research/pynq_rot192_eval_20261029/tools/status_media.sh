set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130575 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026/pynq_rot192_eval_20261029
tail -n 10 logs/media-130575.out
tail -n 8 logs/media-130575.err
if test -f results/media/media_metadata.json; then head -n 28 results/media/media_metadata.json; fi
