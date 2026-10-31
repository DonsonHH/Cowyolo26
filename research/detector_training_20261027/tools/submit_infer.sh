set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/detector_training
job=$(cat "$ROOT/logs/train_job_id.txt")
test "$(sacct -j "$job" -X --format=State --noheader | tr -d ' ')" = COMPLETED
test -s "$ROOT/results/training/all_checkpoints_frozen_before_video.json"
test ! -e "$ROOT/results/inference"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/infer.slurm" | tee "$ROOT/logs/infer_job_id.txt"
