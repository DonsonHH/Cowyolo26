set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
root="$project/activation_range_20261028"
test ! -e "$root"
mkdir "$root"
tar -xzf "$project/activation_range_20261028_staging.tar.gz" -C "$root"
cd "$root"
mkdir logs results
sha256sum protocol/activation_range_v1.json tools/probe.py
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/probe.slurm)
printf '%s\n' "$jobid" > probe_job_id.txt
printf 'ACTIVATION_RANGE_PROBE_JOB_ID=%s\n' "$jobid"
