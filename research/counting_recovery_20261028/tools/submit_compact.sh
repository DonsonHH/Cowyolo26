set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028
cd "$root"
test ! -e compact_job_id.txt
/share/home/renly/miniconda3/envs/sd/bin/ffmpeg -version | head -n 1
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/compact.slurm)
printf '%s\n' "$jobid" > compact_job_id.txt
printf 'COMPACT_VIDEO_JOB_ID=%s\n' "$jobid"
