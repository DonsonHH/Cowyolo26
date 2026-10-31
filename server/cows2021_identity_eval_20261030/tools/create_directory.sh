set -euo pipefail
task_dir=/share/home/renly/projects/idcoo_research_20261026/cows2021_identity_eval_20261030
test ! -e "$task_dir"
mkdir "$task_dir"
mkdir "$task_dir/logs"
printf '%s\n' 'COWS2021_IDENTITY_TASK_DIRECTORY_CREATED_NO_EXISTING_FILE_REPLACED'
