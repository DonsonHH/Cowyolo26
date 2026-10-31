set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028
cd "$root"
test "$(sacct -j 129983 -X -n -o State | xargs)" = COMPLETED
test ! -e optimizer_collect_job_id.txt
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/optimizer_collect.slurm)
printf '%s\n' "$jobid" > optimizer_collect_job_id.txt
printf 'OPTIMIZER_COLLECT_JOB_ID=%s\n' "$jobid"
