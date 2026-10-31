set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
test -f /home/xilinx/jupyter_notebooks/cow_research_validation_v2_20261029/recovery_record.json
chown xilinx:xilinx /home/xilinx/jupyter_notebooks/cow_research_validation_v2_20261029
stat -c '%U|%G|%a|%n' /home/xilinx/jupyter_notebooks/cow_research_validation_v2_20261029
