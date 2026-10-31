set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
stage="$project/cows2021_adaptation_20261027"
test ! -e "$stage/results/download_attempt_02"
test ! -e "$stage/results/transfer_resume_01_to_02.json"
"$project/env/bin/python" -u "$stage/tools/resume_transfer_after_failure.py" --previous 01 --next 02
