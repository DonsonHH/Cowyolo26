set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/composition_control
job=$(cat "$ROOT/logs/preflight_job_id.txt")
test "$(sacct -j "$job" -X --format=State --noheader | tr -d ' ')" = COMPLETED
test -s "$ROOT/results/preflight.json"
test ! -e "$ROOT/results/training"
test ! -e "$ROOT/logs/train0_job_id.txt"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --array=0 --parsable "$ROOT/tools/train.slurm" | tee "$ROOT/logs/train0_job_id.txt"
