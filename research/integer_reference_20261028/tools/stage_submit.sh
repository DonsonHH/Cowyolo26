set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
target="$project/integer_reference_20261028"
test ! -e "$target"
mkdir -p "$target"
tar -xzf "$project/integer_reference_20261028_staging.tar.gz" -C "$target"
cd "$target"
mkdir logs
sha256sum protocol/integer_conv_v1.json tools/run_reference.py tools/integer_math.py
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/reference.slurm)
printf '%s\n' "$jobid" > job_id.txt
printf 'INTEGER_REFERENCE_JOB_ID=%s\n' "$jobid"
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
