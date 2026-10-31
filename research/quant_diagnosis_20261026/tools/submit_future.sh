set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/quant_diagnosis
test -s "$ROOT/catalog/future_holdout/stage_complete.json"
test ! -e "$ROOT/results/future_holdout"
test -s "$ROOT/protocol/future_comparison_frozen.json"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/future.slurm" | tee "$ROOT/logs/future_job_id.txt"
