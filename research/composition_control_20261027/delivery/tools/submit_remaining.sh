set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/composition_control
first=$(cat "$ROOT/logs/train0_job_id.txt")
test "$(sacct -j "${first}_0" -X --format=State --noheader | tr -d ' ')" = COMPLETED
test -s "$ROOT/results/training/mixed_seed26/condition_complete.json"
test ! -e "$ROOT/logs/train_job_id.txt"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
# Live gate found both4gpu nodes idle; run at most2 independent processes.
sbatch --array=1-5%2 --parsable "$ROOT/tools/train.slurm" | tee "$ROOT/logs/train_job_id.txt"
