set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028
cd "$root"
test "$(sacct -j 130222 -X -n -o State | xargs)" = FAILED
test ! -e compact_v2_job_id.txt
test ! -e results/compact_delivery.tar.gz
test -z "$(find results/replay_v2 results/full640_confirmation -name transfer_h264.mp4 -type f -print -quit)"
/share/home/renly/miniconda3/envs/pid310_gpu/bin/ffmpeg -hide_banner -encoders 2>/dev/null | grep 'libx264 '
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/compact_v2.slurm)
printf '%s\n' "$jobid" > compact_v2_job_id.txt
printf 'COMPACT_VIDEO_RETRY_JOB_ID=%s\n' "$jobid"
