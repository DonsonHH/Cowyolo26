set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/identity_training
test -s "$ROOT/logs/study_job_id.txt"
study=$(cat "$ROOT/logs/study_job_id.txt")
test ! -e "$ROOT/results/checkpoint_verification"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable --dependency="afterok:$study" "$ROOT/tools/verify_models.slurm" | tee "$ROOT/logs/reload_job_id.txt"
