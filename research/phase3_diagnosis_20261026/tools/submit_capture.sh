set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/phase3_diagnosis
mkdir -p "$ROOT/logs" "$ROOT/results"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
test ! -e "$ROOT/results/capture"
sbatch --parsable "$ROOT/tools/capture.slurm" | tee "$ROOT/logs/capture_job_id.txt"
