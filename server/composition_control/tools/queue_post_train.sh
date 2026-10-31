set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/composition_control
first=$(cat "$ROOT/logs/train0_job_id.txt")
rest=$(cat "$ROOT/logs/train_job_id.txt")
test ! -e "$ROOT/logs/freeze_job_id.txt"
test ! -e "$ROOT/results/all_models_frozen.json"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
freeze=$(sbatch --dependency="afterok:${first}:${rest}" --parsable "$ROOT/tools/freeze.slurm")
printf '%s\n' "$freeze" | tee "$ROOT/logs/freeze_job_id.txt"
sbatch --dependency="afterok:${freeze}" --parsable "$ROOT/tools/infer.slurm" | tee "$ROOT/logs/infer_job_id.txt"
