set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/phase3_diagnosis
test "$(sacct -j 129691 -X --format=State --noheader | tr -d ' ')" = FAILED
test -d "$ROOT/results/capture"
test ! -e "$ROOT/results/capture_failed_129691"
mv -- "$ROOT/results/capture" "$ROOT/results/capture_failed_129691"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/capture.slurm" | tee "$ROOT/logs/capture_job_id.txt"
