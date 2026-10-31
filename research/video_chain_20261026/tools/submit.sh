set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/video_chain
mkdir -p "$ROOT/logs"
test ! -e "$ROOT/results/replay"
test -s /share/home/renly/projects/idcoo_research_20261026/identity_training/results/study/summary.json
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/replay.slurm" | tee "$ROOT/logs/job_id.txt"
