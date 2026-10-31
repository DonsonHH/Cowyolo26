set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/composition_control
test "$(sacct -j 129835 -X --format=State --noheader | tr -d ' ')" = FAILED
test "$(sacct -j 129836 -X --format=State --noheader | tr -d ' ')" = COMPLETED
test -s "$ROOT/results/loader_label_diagnosis.json"
test ! -e "$ROOT/results/preflight.json"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/preflight.slurm" | tee "$ROOT/logs/preflight_job_id.txt"
