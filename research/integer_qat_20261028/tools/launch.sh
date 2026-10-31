set -euo pipefail
archive=/share/home/renly/projects/idcoo_research_20261026/integer_qat_20261028_staging.tar.gz
printf 'c5c180a5bda13279441dda547b2a5b84b570cd0d492a21c437af0c0c7703adff  %s\n' "$archive" | sha256sum -c -
tar -xOzf "$archive" tools/stage_submit.sh | bash
