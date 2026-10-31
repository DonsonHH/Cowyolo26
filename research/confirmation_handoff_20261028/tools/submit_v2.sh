set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/confirmation_handoff_20261028
cd "$root"
test "$(sacct -j "$(cat job_id.txt)" -X -n -o State | xargs)" = FAILED
test ! -e v2_job_id.txt
test ! -e results/replay_v2
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/replay_v2.slurm)
printf '%s\n' "$jobid" > v2_job_id.txt
printf 'CONFIRMATION_HANDOFF_V2_JOB_ID=%s\n' "$jobid"
