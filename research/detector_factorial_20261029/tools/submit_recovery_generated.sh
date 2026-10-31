set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
cd /share/home/renly/projects/idcoo_research_20261026
test ! -e detector_factorial_20261029/results/all_checkpoints_frozen.json
sbatch --parsable --dependency=afterany:130518 detector_factorial_20261029/tools/recover.slurm
