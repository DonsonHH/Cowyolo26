set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028
cd "$root"
test "$(sacct -j 129981 -X -n -o State | xargs)" = COMPLETED
test ! -e optimizer_isolation_job_id.txt
test ! -e results/optimizer_isolation
sha256sum protocol/optimizer_isolation_v1.json tools/isolate_optimizer_add.py
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/optimizer_isolation.slurm)
printf '%s\n' "$jobid" > optimizer_isolation_job_id.txt
printf 'OPTIMIZER_ISOLATION_JOB_ID=%s\n' "$jobid"
