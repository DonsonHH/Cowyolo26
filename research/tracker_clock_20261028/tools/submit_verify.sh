set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/tracker_clock_20261028
cd "$root"
jobid=$(cat job_id.txt)
test "$(sacct -j "$jobid" -X -n -o State | xargs)" = COMPLETED
test ! -e verify_job_id.txt
test ! -e results/independent_verification.json
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
verifyid=$(sbatch --parsable tools/verify.slurm)
printf '%s\n' "$verifyid" > verify_job_id.txt
printf 'TRACKER_CLOCK_VERIFY_JOB_ID=%s\n' "$verifyid"
