set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly
test ! -e /share/home/renly/projects/idcoo_research_20261026/backend_service_20261030
mkdir /share/home/renly/projects/idcoo_research_20261026/backend_service_20261030
