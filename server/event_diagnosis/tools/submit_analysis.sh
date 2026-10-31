set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/event_diagnosis
job=$(cat "$ROOT/logs/capture_job_id.txt")
test "$(sacct -j "$job" -X --format=State --noheader | tr -d ' ')" = COMPLETED
test -s "$ROOT/results/capture/summary.json"
test ! -e "$ROOT/results/layers"
test ! -e "$ROOT/results/source_cases"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/layers.slurm" | tee "$ROOT/logs/layers_job_id.txt"
sbatch --parsable "$ROOT/tools/source.slurm" | tee "$ROOT/logs/source_job_id.txt"
