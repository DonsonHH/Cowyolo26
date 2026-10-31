set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_qat_20261028
cd "$root"
jobid=$(cat verify_job_id.txt)
test "$(sacct -j "$jobid" -X -n -o State | xargs)" = COMPLETED
test ! -e collect_job_id.txt
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/collect.slurm)
printf '%s\n' "$jobid" > collect_job_id.txt
printf 'PAIRED_INTEGER_QAT_COLLECTION_JOB_ID=%s\n' "$jobid"
