set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/detector_training
mkdir -p "$ROOT/logs"
test ! -e "$ROOT/results/training"
sinfo -o '%P|%a|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/train.slurm" | tee "$ROOT/logs/train_job_id.txt"
