set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028
cd "$root"
test -s results/replay_v2/full640_5hz_seed26/summary.json
test ! -e full640_job_id.txt
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/confirm_full640.slurm)
printf '%s\n' "$jobid" > full640_job_id.txt
printf 'FULL640_CONFIRMATION_JOB_ID=%s\n' "$jobid"
