set -euo pipefail
stage=/share/home/renly/projects/idcoo_research_20261026/orientation_video_20261027
test "$(cat "$stage/results/replay_job_id.txt")" = 129940
test ! -e "$stage/results/collection_job_id.txt"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%R'
jobid=$(sbatch --parsable --dependency=afterok:129940 "$stage/tools/collect.slurm")
printf '%s\n' "$jobid" > "$stage/results/collection_job_id.txt"
printf 'replay=129940\ncollection=%s\n' "$jobid"
