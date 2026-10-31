set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/video_chain
job=$(cat "$ROOT/logs/job_id.txt")
test "$(sacct -j "$job" -X --format=State --noheader | tr -d ' ')" = COMPLETED
test -s "$ROOT/results/replay/events.json"
test ! -e "$ROOT/results/verification"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/verify.slurm" | tee "$ROOT/logs/verify_job_id.txt"
