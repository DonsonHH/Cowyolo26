set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028
cd "$root"
test "$(sacct -j 129982 -X -n -o State | xargs)" = COMPLETED
test ! -e optimizer_verify_job_id.txt
sha256sum tools/verify_optimizer_controls.py tools/optimizer_verify.slurm
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/optimizer_verify.slurm)
printf '%s\n' "$jobid" > optimizer_verify_job_id.txt
printf 'OPTIMIZER_VERIFY_JOB_ID=%s\n' "$jobid"
