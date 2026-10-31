set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_qat_20261028
cd "$root"
test "$(sacct -j 129998 -X -n -o State | xargs)" = COMPLETED
test -s results/study/summary.json
test ! -e verify_job_id.txt
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/verify.slurm)
printf '%s\n' "$jobid" > verify_job_id.txt
printf 'PAIRED_INTEGER_QAT_VERIFY_JOB_ID=%s\n' "$jobid"
