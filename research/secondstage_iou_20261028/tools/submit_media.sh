set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/secondstage_iou_20261028
cd "$root"
test "$(sacct -j "$(cat replay_job_id.txt)" -X -n -o State | xargs)" = COMPLETED
test ! -e media_job_id.txt
test ! -e results/render_verification.json
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sha256sum results/local_verification.json protocol/render_v1.json
jobid=$(sbatch --parsable tools/render_media.slurm)
printf '%s\n' "$jobid" > media_job_id.txt
printf 'SECONDSTAGE_MEDIA_JOB_ID=%s\n' "$jobid"
