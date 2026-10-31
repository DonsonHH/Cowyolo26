set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
target="$project/counting_recovery_20261028"
test ! -e "$target"
mkdir "$target"
tar -xzf "$project/counting_recovery_20261028_staging.tar.gz" -C "$target"
cd "$target"
mkdir logs results
sha256sum protocol/recovery_v1.json tools/replay.py tools/native_restore.py
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/replay.slurm)
printf '%s\n' "$jobid" > job_id.txt
printf 'RECOVERY_JOB_ID=%s\n' "$jobid"
