set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
cd /share/home/renly/projects/idcoo_research_20261026/lowres_baseline_20261029
test "$(sacct -j 130502 --noheader --format=State -P | head -n1)" = FAILED
test -s results/baseline/validation_metrics.json
test ! -e results/baseline/toros
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sbatch --parsable --job-name=cow-lowres-toros --partition=4gpu --nodes=1 --ntasks=1 --gres=gpu:V100S:1 --cpus-per-task=8 --mem=12G --time=00:10:00 --output=logs/toros-%j.out --error=logs/toros-%j.err --wrap='../env/bin/python tools/finish_toros.py'
