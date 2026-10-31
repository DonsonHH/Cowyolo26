set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
cd /share/home/renly/projects/idcoo_research_20261026/detector_torso_pairs_20261029
test ! -e results/plots
sbatch --parsable --job-name=cow-torso-plot --partition=4gpu --nodes=1 --ntasks=1 --cpus-per-task=1 --mem=2G --time=00:05:00 --output=logs/plot-%j.out --error=logs/plot-%j.err --wrap='../env/bin/python tools/plot_results.py'
