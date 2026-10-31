set -euo pipefail
r=/share/home/renly/projects/idcoo_research_20261026/identity_domain_ncnn_20261030
test ! -e "$r"
mkdir "$r"
mkdir "$r/logs"
printf '%s\n' 'NEW_NCNN_TASK_DIRECTORY_CREATED_NO_OVERWRITE'
