set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/qat_study
job=$(cat "$ROOT/logs/smoke_job_id.txt")
test "$(sacct -j "$job" -X --format=State --noheader | tr -d ' ')" = COMPLETED
test -s "$ROOT/results/smoke/summary.json"
test ! -e "$ROOT/results/study"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/study.slurm" | tee "$ROOT/logs/study_job_id.txt"
