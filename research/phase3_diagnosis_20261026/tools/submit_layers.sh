set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/phase3_diagnosis
test "$(sacct -j 129692 -X --format=State --noheader | tr -d ' ')" = COMPLETED
test -s "$ROOT/results/capture/summary.json"
test ! -e "$ROOT/results/layers"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/layers.slurm" | tee "$ROOT/logs/layers_job_id.txt"
