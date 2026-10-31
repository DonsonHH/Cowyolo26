set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/confirmation_handoff_20261028
cd "$root"
test "$(sacct -j "$(cat v2_job_id.txt)" -X -n -o State | xargs)" = COMPLETED
test ! -e verify_media_job_id.txt
test ! -e results/independent_verification.json
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/verify_render.slurm)
printf '%s\n' "$jobid" > verify_media_job_id.txt
printf 'HANDOFF_VERIFY_MEDIA_JOB_ID=%s\n' "$jobid"
