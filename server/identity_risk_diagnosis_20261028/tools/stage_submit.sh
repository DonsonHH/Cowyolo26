set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
root="$project/identity_risk_diagnosis_20261028"
test ! -e "$root"
mkdir "$root"
tar -xzf "$project/identity_risk_diagnosis_20261028_staging.tar.gz" -C "$root"
cd "$root"
mkdir logs
sha256sum tools/render.py input/independent_verification.json
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/render.slurm)
printf '%s\n' "$jobid" > render_job_id.txt
printf 'IDENTITY_RISK_RENDER_JOB_ID=%s\n' "$jobid"
