set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/qat_study
test "$(sacct -j 129738 -X --format=State --noheader | tr -d ' ')" = FAILED
test -d "$ROOT/results/smoke"
test ! -e "$ROOT/results/smoke_failed_129738"
mv "$ROOT/results/smoke" "$ROOT/results/smoke_failed_129738"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/smoke.slurm" | tee "$ROOT/logs/smoke_job_id.txt"
