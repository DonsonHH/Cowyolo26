set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/detector_training
train=$(cat "$ROOT/logs/train_job_id.txt")
test "$(sacct -j "$train" -X --format=State --noheader | tr -d ' ')" = RUNNING
test ! -e "$ROOT/logs/infer_job_id.txt"
test ! -e "$ROOT/results/inference"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --dependency="afterok:${train}" --parsable "$ROOT/tools/infer.slurm" | tee "$ROOT/logs/infer_job_id.txt"
