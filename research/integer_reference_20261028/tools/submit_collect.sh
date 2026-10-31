set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028
cd "$root"
test "$(sacct -j 129977 -X -n -o State | xargs)" = COMPLETED
test ! -e collection_job_id.txt
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/collect.slurm)
printf '%s\n' "$jobid" > collection_job_id.txt
printf 'INTEGER_REFERENCE_COLLECTION_JOB_ID=%s\n' "$jobid"
