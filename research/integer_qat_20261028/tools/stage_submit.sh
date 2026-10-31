set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
root="$project/integer_qat_20261028"
test ! -e "$root"
mkdir "$root"
tar -xzf "$project/integer_qat_20261028_staging.tar.gz" -C "$root"
cd "$root"
mkdir logs results
sha256sum protocol/paired_integer_qat_v1.json tools/train.py
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/train.slurm)
printf '%s\n' "$jobid" > train_job_id.txt
printf 'PAIRED_INTEGER_QAT_JOB_ID=%s\n' "$jobid"
