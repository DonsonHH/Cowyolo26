set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/quant_diagnosis
future=$(cat "$ROOT/logs/future_job_id.txt")
test "$(sacct -j "$future" -X --format=State --noheader | tr -d ' ')" = COMPLETED
test ! -e "$ROOT/results/portability_probe"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/portability.slurm" | tee "$ROOT/logs/portability_job_id.txt"
