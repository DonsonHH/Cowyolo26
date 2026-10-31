set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
cd /share/home/renly/projects/idcoo_research_20261026/detector_torso_pairs_20261029
test ! -e results/input_controls
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sbatch --parsable --job-name=cow-torso-input --partition=4gpu --nodes=1 --ntasks=1 --gres=gpu:V100S:1 --cpus-per-task=8 --mem=8G --time=00:05:00 --output=logs/input-%j.out --error=logs/input-%j.err --wrap='../env/bin/python tools/input_controls.py'
