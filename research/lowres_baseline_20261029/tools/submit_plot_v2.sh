set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
cd /share/home/renly/projects/idcoo_research_20261026/lowres_baseline_20261029
test ! -e results/plots_v2
sbatch --parsable --job-name=cow-lowres-plot-v2 --partition=4gpu --nodes=1 --ntasks=1 --cpus-per-task=1 --mem=2G --time=00:05:00 --output=logs/plot-v2-%j.out --error=logs/plot-v2-%j.err --wrap='../env/bin/python tools/render_plot_v2.py'
