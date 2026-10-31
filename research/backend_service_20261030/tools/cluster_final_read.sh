set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130717 --format=JobID,State,ExitCode,Elapsed,AllocCPUS
wc -c /share/home/renly/projects/idcoo_research_20261026/backend_service_20261030/logs/reference-130717.err
