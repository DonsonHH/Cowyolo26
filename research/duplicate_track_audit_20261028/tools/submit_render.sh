set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/duplicate_track_audit_20261028
cd "$root"
test ! -e render_job_id.txt
test ! -e results/figures
mkdir -p results logs
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sha256sum protocol/render_v1.json tools/render.py results/audit.json results/independent_verification.json
jobid=$(sbatch --parsable tools/render.slurm)
printf '%s\n' "$jobid" > render_job_id.txt
printf 'DUPLICATE_AUDIT_RENDER_JOB_ID=%s\n' "$jobid"
