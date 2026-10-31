set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/duplicate_track_audit_20261028
cd "$root"
test "$(sacct -j "$(cat render_job_id.txt)" -X -n -o State | xargs)" = COMPLETED
test ! -e render_v2_job_id.txt
test ! -e results/figures_v2
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/render_v2.slurm)
printf '%s\n' "$jobid" > render_v2_job_id.txt
printf 'LAYOUT_FIXED_RENDER_JOB_ID=%s\n' "$jobid"
