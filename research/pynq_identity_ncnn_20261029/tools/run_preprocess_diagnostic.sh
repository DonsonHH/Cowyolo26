set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
cd /home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029
/usr/local/share/pynq-venv/bin/python3 -u -B diagnose_preprocess.py
