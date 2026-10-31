set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/quant_diagnosis
mkdir -p "$ROOT/logs"
test ! -e "$ROOT/results/activations"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/activation.slurm" | tee "$ROOT/logs/activation_job_id.txt"
