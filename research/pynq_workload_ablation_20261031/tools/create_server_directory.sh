set -euo pipefail
test "$(id -un)" = xilinx
test ! -e /home/xilinx/jupyter_notebooks/cow_research_workload_ablation_20261031
mkdir /home/xilinx/jupyter_notebooks/cow_research_workload_ablation_20261031
printf 'FRESH_WORKLOAD_ABLATION_DIRECTORY_CREATED\n'
