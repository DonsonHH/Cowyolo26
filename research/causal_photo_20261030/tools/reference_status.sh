set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -j 130642 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 130642 --format=JobID,JobName%24,State,ExitCode,Elapsed,AllocCPUS,MaxRSS
cd /share/home/renly/projects/idcoo_research_20261026/causal_photo_20261030
tail -n 6 logs/reference-130642.out
tail -n 12 logs/reference-130642.err
if test -f reference_transfer.json; then cat reference_transfer.json; fi
