set -euo pipefail
archive=/share/home/renly/projects/idcoo_research_20261026/activation_range_20261028_staging.tar.gz
printf 'a06f2bce5f0a915d3eba0b69cc0c0e350aae950ee4aef3c4e31107b3b3dba9e0  %s\n' "$archive" | sha256sum -c -
tar -xOzf "$archive" tools/stage_submit.sh | bash
