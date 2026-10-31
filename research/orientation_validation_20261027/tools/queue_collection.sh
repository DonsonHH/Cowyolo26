set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
stage="$project/orientation_validation_20261027"
test "$(cat "$stage/results/control_job_id.txt")" = 129929
test ! -e "$stage/results/collection_job_id.txt"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable --dependency=afterok:129929 "$stage/tools/collect.slurm")
printf '%s\n' "$jobid" > "$stage/results/collection_job_id.txt"
printf 'control=129929\ncollection=%s\n' "$jobid"
squeue -j "129929,$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
