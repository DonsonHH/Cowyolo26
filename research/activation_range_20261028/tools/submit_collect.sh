set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/activation_range_20261028
cd "$root"
test "$(sacct -j 130004 -X -n -o State | xargs)" = COMPLETED
test ! -e collect_job_id.txt
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/collect.slurm)
printf '%s\n' "$jobid" > collect_job_id.txt
printf 'ACTIVATION_RANGE_COLLECTION_JOB_ID=%s\n' "$jobid"
