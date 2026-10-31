set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130593 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026/pynq_o8_sizes_20261030
tail -n 4 logs/compile-130593_0.out
tail -n 4 logs/compile-130593_1.out
tail -n 4 logs/compile-130593_0.err
tail -n 4 logs/compile-130593_1.err
