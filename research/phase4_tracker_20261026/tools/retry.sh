set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/phase4_tracker
test "$(sacct -j 129694 -X --format=State --noheader | tr -d ' ')" = FAILED
test -d "$ROOT/results/replay"
test ! -e "$ROOT/results/replay_failed_129694"
mv -- "$ROOT/results/replay" "$ROOT/results/replay_failed_129694"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/replay.slurm" | tee "$ROOT/logs/job_id.txt"
