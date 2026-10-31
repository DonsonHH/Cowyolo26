set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/external_method_regression_20261028
cd "$root"
test "$(sacct -j "$(cat job_id.txt)" -X -n -o State | xargs)" = COMPLETED
test ! -e case_job_id.txt
test ! -e results/case
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/render_case.slurm)
printf '%s\n' "$jobid" > case_job_id.txt
printf 'EXTERNAL_CASE_JOB_ID=%s\n' "$jobid"
