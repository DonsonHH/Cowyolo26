set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/composition_control
infer=$(cat "$ROOT/logs/infer_job_id.txt")
test ! -e "$ROOT/logs/collect_job_id.txt"
test ! -e "$ROOT/delivery.tar.gz"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --dependency="afterok:${infer}" --parsable "$ROOT/tools/collect.slurm" | tee "$ROOT/logs/collect_job_id.txt"
