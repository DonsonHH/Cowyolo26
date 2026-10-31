set -euo pipefail
task_dir=/share/home/renly/projects/idcoo_research_20261026/identity_domain_adapt_20261030
test ! -e "$task_dir"
mkdir "$task_dir"
mkdir "$task_dir/logs"
printf '%s\n' 'DOMAIN_ADAPT_TASK_DIRECTORY_CREATED_WITHOUT_REPLACING_EXISTING_FILES'
