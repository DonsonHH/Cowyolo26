set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/detector_training
test "$(sacct -j 129785 -X --format=State --noheader | tr -d ' ')" = COMPLETED
test ! -e "$ROOT/results/checkpoint_reload.json"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/reload.slurm" | tee "$ROOT/logs/reload_job_id.txt"
