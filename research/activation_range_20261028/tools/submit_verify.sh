set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/activation_range_20261028
cd "$root"
test "$(sacct -j 130003 -X -n -o State | xargs)" = COMPLETED
test ! -e verify_job_id.txt
sha256sum tools/independent_verify.py
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/verify.slurm)
printf '%s\n' "$jobid" > verify_job_id.txt
printf 'ACTIVATION_RANGE_VERIFY_JOB_ID=%s\n' "$jobid"
