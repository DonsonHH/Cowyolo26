set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 130643 --format=JobID,State,ExitCode,Elapsed,AllocCPUS
wc -c /share/home/renly/projects/idcoo_research_20261026/async_highres_20261030/logs/reference-130643.err
