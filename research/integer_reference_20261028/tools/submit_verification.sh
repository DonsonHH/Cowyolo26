set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028
cd "$root"
test "$(sacct -j 129976 -X -n -o State | xargs)" = COMPLETED
test -s results/reference/summary.json
test ! -e verification_job_id.txt
sha256sum tools/independent_verify.py tools/verify.slurm
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/verify.slurm)
printf '%s\n' "$jobid" > verification_job_id.txt
printf 'INTEGER_REFERENCE_VERIFY_JOB_ID=%s\n' "$jobid"
