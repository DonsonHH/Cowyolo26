set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/composition_control
test "$(sacct -j 129835 -X --format=State --noheader | tr -d ' ')" = FAILED
test ! -e "$ROOT/results/loader_label_diagnosis.json"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/labels.slurm" | tee "$ROOT/logs/labels_job_id.txt"
