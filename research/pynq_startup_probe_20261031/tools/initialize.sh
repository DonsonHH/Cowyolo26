set -euo pipefail
test "$(id -un)" = xilinx
test ! -e /home/xilinx/jupyter_notebooks/cow_research_startup_probe_20261031
mkdir /home/xilinx/jupyter_notebooks/cow_research_startup_probe_20261031
printf '%s\n' 'Fresh isolated startup diagnostic directory created.'
