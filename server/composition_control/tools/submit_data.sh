set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/composition_control
mkdir -p "$ROOT/logs"
test ! -e "$ROOT/data"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/prepare.slurm" | tee "$ROOT/logs/prepare_job_id.txt"
