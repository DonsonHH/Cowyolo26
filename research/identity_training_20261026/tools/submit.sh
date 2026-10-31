set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/identity_training
test -s "$ROOT/catalog/stage_complete.json"
test ! -e "$ROOT/results/input_audit"
test ! -e "$ROOT/results/study"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
audit=$(sbatch --parsable "$ROOT/tools/audit.slurm")
echo "$audit" | tee "$ROOT/logs/audit_job_id.txt"
study=$(sbatch --parsable --dependency="afterok:$audit" "$ROOT/tools/study.slurm")
echo "$study" | tee "$ROOT/logs/study_job_id.txt"
