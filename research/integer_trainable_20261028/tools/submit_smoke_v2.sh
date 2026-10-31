set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_trainable_20261028
cd "$root"
test "$(sacct -j 129989 -X -n -o State | xargs)" = FAILED
test "$(sacct -j 129990 -X -n -o State | xargs)" = COMPLETED
test ! -e smoke_v2_job_id.txt
test ! -e results/smoke_v2
sha256sum protocol/trainable_integer_smoke_v1.json tools/smoke_v2.py tools/integer_trainable.py
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/smoke_v2.slurm)
printf '%s\n' "$jobid" > smoke_v2_job_id.txt
printf 'TRAINABLE_INTEGER_SMOKE_V2_JOB_ID=%s\n' "$jobid"
