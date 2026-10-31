set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/deployment_audit
test ! -e "$ROOT/results/export_audit"
test -s "$ROOT/dependencies_offline/onnx/__init__.py"
test -s "$ROOT/dependencies_offline/onnxruntime/__init__.py"
PYTHONPATH="$ROOT/dependencies_offline" /share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
import onnx,onnxruntime,numpy
assert onnx.__version__=='1.19.0'
assert onnxruntime.__version__=='1.23.2'
assert numpy.__version__=='2.2.6'
print('Pinned export packages import; heavy graph work is scheduled below.')
PY
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/audit.slurm" | tee "$ROOT/logs/job_id.txt"
