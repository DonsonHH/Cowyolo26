set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/source_demo
mkdir -p "$ROOT/logs"
test ! -e "$ROOT/results/preview"
sinfo -o '%P|%a|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/preview.slurm" | tee "$ROOT/logs/preview_job_id.txt"
