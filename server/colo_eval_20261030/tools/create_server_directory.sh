set -euo pipefail
task_dir=/share/home/renly/projects/idcoo_research_20261026/colo_eval_20261030
test ! -e "$task_dir"
mkdir "$task_dir"
mkdir "$task_dir/logs"
printf '%s\n' 'NEW_COLO_TASK_DIRECTORY_CREATED_WITHOUT_REPLACING_EXISTING_FILES'
