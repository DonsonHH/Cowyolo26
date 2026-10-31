set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/quant_diagnosis
test "$(sacct -j 129721 -X --format=State --noheader | tr -d ' ')" = COMPLETED
test ! -e "$ROOT/results/mixed"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/mixed.slurm" | tee "$ROOT/logs/mixed_job_id.txt"
