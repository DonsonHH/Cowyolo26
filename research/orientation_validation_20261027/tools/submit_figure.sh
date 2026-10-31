set -euo pipefail
stage=/share/home/renly/projects/idcoo_research_20261026/orientation_validation_20261027
test -f "$stage/results/control/summary.json"
test ! -e "$stage/figures"
test ! -e "$stage/results/figure_record.json"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%R'
jobid=$(sbatch --parsable "$stage/tools/plot.slurm")
printf '%s\n' "$jobid" > "$stage/results/figure_job_id.txt"
printf '%s\n' "$jobid"
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%R'
