set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
root="$project/integer_trainable_20261028"
test ! -e "$root"
mkdir "$root"
tar -xzf "$project/integer_trainable_20261028_staging.tar.gz" -C "$root"
cd "$root"
mkdir logs results
export PYTHONPATH="$project/deployment_audit/dependencies_offline"
"$project/env/bin/python" -c 'import torch,onnx,onnxruntime; print(torch.__version__,onnx.__version__,onnxruntime.__version__)'
sha256sum protocol/trainable_integer_smoke_v1.json tools/smoke.py tools/integer_trainable.py
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/smoke.slurm)
printf '%s\n' "$jobid" > smoke_job_id.txt
printf 'TRAINABLE_INTEGER_SMOKE_JOB_ID=%s\n' "$jobid"
