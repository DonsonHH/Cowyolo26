set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/lost_recovery_20261028
cd "$root"
test "$(sacct -j "$(cat red_job_id.txt)" -X -n -o State | xargs)" = COMPLETED
test ! -e replay_job_id.txt
test ! -e results/summary.json
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sha256sum protocol/lost_v1.json tools/lost_tracker.py input/secondstage_tracker.py
jobid=$(sbatch --parsable tools/replay.slurm)
printf '%s\n' "$jobid" > replay_job_id.txt
printf 'LOST_PAIRED_REPLAY_JOB_ID=%s\n' "$jobid"
