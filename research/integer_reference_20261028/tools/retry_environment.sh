set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028
cd "$root"
test "$(sacct -j 129975 -X -n -o State | xargs)" = FAILED
test ! -e results/reference/summary.json
export PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/deployment_audit/dependencies_offline
/share/home/renly/projects/idcoo_research_20261026/env/bin/python -c 'import onnx, onnxruntime, numpy; print("DEPENDENCY_PREFLIGHT", onnx.__version__, onnxruntime.__version__, numpy.__version__)'
sha256sum protocol/integer_conv_v1.json tools/run_reference.py tools/integer_math.py tools/reference_v2.slurm
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/reference_v2.slurm)
printf '%s\n' "$jobid" > job_id_v2.txt
printf 'INTEGER_REFERENCE_RETRY_JOB_ID=%s\n' "$jobid"
