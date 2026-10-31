set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
test ! -e /share/home/renly/projects/idcoo_research_20261026/pynq_parent_only_trigger_20261031
mkdir -p /share/home/renly/projects/idcoo_research_20261026/pynq_parent_only_trigger_20261031/logs
printf '%s\n' 'Fresh dynamic-trigger reference directory created.'
