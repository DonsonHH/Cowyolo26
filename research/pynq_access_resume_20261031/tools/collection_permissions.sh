set -euo pipefail
test "$(id -un)" = xilinx
ls -ld /home/xilinx/jupyter_notebooks /home/xilinx/jupyter_notebooks/cow_research_identity_trigger_pair_20261030
test ! -e /home/xilinx/jupyter_notebooks/cow_research_access_resume_20261031
mkdir /home/xilinx/jupyter_notebooks/cow_research_access_resume_20261031
printf 'NEW_RECOVERY_HELPER_DIRECTORY_READY\n'
