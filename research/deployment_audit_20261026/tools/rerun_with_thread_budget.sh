set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/deployment_audit
test "$(sacct -j 129719 -X --format=State --noheader | tr -d ' ')" = COMPLETED
test -s "$ROOT/results/export_audit/summary.json"
test ! -e "$ROOT/results/export_audit_initial_129719"
grep -q 'pthread_setaffinity_np failed' "$ROOT/logs/audit-129719.err"
mv -- "$ROOT/results/export_audit" "$ROOT/results/export_audit_initial_129719"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/audit.slurm" | tee "$ROOT/logs/job_id.txt"
