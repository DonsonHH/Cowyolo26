set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
cd /share/home/renly/projects/idcoo_research_20261026/lowres_baseline_20261029
test ! -e results/media
sbatch --parsable --job-name=cow-lowres-media --partition=4gpu --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=4G --time=00:10:00 --output=logs/media-%j.out --error=logs/media-%j.err --wrap='../env/bin/python tools/render_media.py'
