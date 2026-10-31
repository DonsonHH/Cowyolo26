set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/identity_baseline
test -s "$ROOT/catalog/stage_complete.json"
test ! -e "$ROOT/results/image_audit"
mkdir -p "$ROOT/results"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/audit.slurm" | tee "$ROOT/logs/audit_job_id.txt"
