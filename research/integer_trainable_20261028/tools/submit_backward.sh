set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_trainable_20261028
cd "$root"
test "$(sacct -j 129989 -X -n -o State | xargs)" = FAILED
test ! -e backward_probe_job_id.txt
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/backward_probe.slurm)
printf '%s\n' "$jobid" > backward_probe_job_id.txt
printf 'TRAINABLE_INTEGER_BACKWARD_JOB_ID=%s\n' "$jobid"
