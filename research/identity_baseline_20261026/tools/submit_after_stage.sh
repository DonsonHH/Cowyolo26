set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/identity_baseline
test -s "$ROOT/catalog/stage_complete.json"
test -s "$ROOT/models/checkpoint_record.json"
test ! -e "$ROOT/results/image_audit"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
audit_job=$(sbatch --parsable "$ROOT/tools/audit.slurm")
echo "$audit_job" | tee "$ROOT/logs/audit_job_id.txt"
baseline_job=$(sbatch --dependency="afterok:$audit_job" --parsable "$ROOT/tools/baseline.slurm")
echo "$baseline_job" | tee "$ROOT/logs/baseline_job_id.txt"
group_job=$(sbatch --dependency="afterok:$baseline_job" --parsable "$ROOT/tools/aggregate.slurm")
echo "$group_job" | tee "$ROOT/logs/aggregate_job_id.txt"
