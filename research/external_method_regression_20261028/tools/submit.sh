set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/external_method_regression_20261028
cd "$root"
test ! -e job_id.txt
test ! -e results/summary.json
mkdir -p logs results
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sha256sum protocol/regression_v1.json tools/replay.py input/*.py input/publisher_gt_original.txt
jobid=$(sbatch --parsable tools/replay.slurm)
printf '%s\n' "$jobid" > job_id.txt
printf 'EXTERNAL_METHOD_REGRESSION_JOB_ID=%s\n' "$jobid"
