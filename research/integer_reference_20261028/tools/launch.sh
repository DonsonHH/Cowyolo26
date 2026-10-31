set -euo pipefail
archive=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028_staging.tar.gz
printf '0fffb0e75e2fe0a3bf8ff932c20035bcc0db7d5d715e1fdc16934db4106d13c7  %s\n' "$archive" | sha256sum -c -
tar -xOzf "$archive" tools/stage_submit.sh | bash
