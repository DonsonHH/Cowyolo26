set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028
cd "$root"
jobid=$(cat retry_job_id.txt)
test "$(sacct -j "$jobid" -X -n -o State | xargs)" = COMPLETED
fulljob=$(cat full640_job_id.txt)
test "$(sacct -j "$fulljob" -X -n -o State | xargs)" = COMPLETED
test -s results/replay_v2/summary.json
test ! -e verify_job_id.txt
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/verify.slurm)
printf '%s\n' "$jobid" > verify_job_id.txt
printf 'RECOVERY_VERIFY_JOB_ID=%s\n' "$jobid"
