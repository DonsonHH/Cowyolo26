set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/composition_control
job=$(cat "$ROOT/logs/prepare_job_id.txt")
test "$(sacct -j "$job" -X --format=State --noheader | tr -d ' ')" = COMPLETED
test -s "$ROOT/results/data_prepared.json"
test ! -e "$ROOT/results/preflight.json"
test ! -e "$ROOT/logs/preflight_job_id.txt"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/preflight.slurm" | tee "$ROOT/logs/preflight_job_id.txt"
