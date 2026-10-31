set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/composition_control
test "$(sacct -j 129841_0 -X --format=State --noheader | tr -d ' ')" = FAILED
test "$(realpath "$ROOT/results/training/mixed_seed26")" = "$ROOT/results/training/mixed_seed26"
test ! -e "$ROOT/results/failed_training/mixed_seed26_129841_0"
mkdir -p "$ROOT/results/failed_training"
mv -- "$ROOT/results/training/mixed_seed26" "$ROOT/results/failed_training/mixed_seed26_129841_0"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --array=0 --parsable "$ROOT/tools/train.slurm" | tee "$ROOT/logs/train0_job_id.txt"
