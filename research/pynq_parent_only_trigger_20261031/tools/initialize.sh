set -euo pipefail
test "$(id -un)" = xilinx
test ! -e /home/xilinx/jupyter_notebooks/cow_research_parent_only_trigger_20261031
mkdir /home/xilinx/jupyter_notebooks/cow_research_parent_only_trigger_20261031
printf '%s\n' 'Fresh parent-only actual-trigger task directory created.'
