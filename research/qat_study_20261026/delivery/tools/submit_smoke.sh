set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/qat_study
mkdir -p "$ROOT/logs"
test ! -e "$ROOT/results/smoke"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/smoke.slurm" | tee "$ROOT/logs/smoke_job_id.txt"
