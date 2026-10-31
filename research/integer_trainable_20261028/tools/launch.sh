set -euo pipefail
archive=/share/home/renly/projects/idcoo_research_20261026/integer_trainable_20261028_staging.tar.gz
printf 'e3672843c6297a6b478a7da0f70ca4565181196c2c0738a7ced1c24365b33b3c  %s\n' "$archive" | sha256sum -c -
tar -xOzf "$archive" tools/stage_submit.sh | bash
