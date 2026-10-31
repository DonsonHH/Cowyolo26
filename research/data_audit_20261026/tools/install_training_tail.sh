set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026
"$ROOT/env/bin/python" -m pip install --no-deps "$ROOT/wheelhouse/polars_runtime_32-2.1.0-cp311-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl" 'polars==2.1.0' > "$ROOT/logs/install_training_tail.log" 2>&1
"$ROOT/env/bin/python" -m pip check > "$ROOT/logs/pip_check_after_dependencies.txt" || true
"$ROOT/env/bin/python" -m pip freeze > "$ROOT/logs/runtime_complete_freeze.txt"
mkdir -p "$ROOT/mpl_cache"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/train_detection_pilot.slurm" | tee "$ROOT/logs/detection_pilot_jobid.txt"
