set -euo pipefail
archive=/share/home/renly/projects/idcoo_research_20261026/identity_risk_diagnosis_20261028_staging.tar.gz
printf 'ae48bde9540ff731e046e236cdbe71fb93c260ce2108fbf3db91d08c6c2ca42a  %s\n' "$archive" | sha256sum -c -
tar -xOzf "$archive" tools/stage_submit.sh | bash
