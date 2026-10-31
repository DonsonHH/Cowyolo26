set -euo pipefail
archive=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028_staging.tar.gz
printf '21c6b2d8c32c5228d675a75eba67bb2a5bb5cb516dc4f85827668638e18d0f75  %s\n' "$archive" | sha256sum -c -
tar -xOzf "$archive" tools/stage_submit.sh | bash
