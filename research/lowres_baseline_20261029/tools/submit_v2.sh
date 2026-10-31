set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
cd /share/home/renly/projects/idcoo_research_20261026/lowres_baseline_20261029
test "$(sacct -j 130501 --noheader --format=State -P | head -n1)" = FAILED
test ! -e results/baseline
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sbatch --parsable --job-name=cow-lowres-v2 --partition=4gpu --nodes=1 --ntasks=1 --gres=gpu:V100S:1 --cpus-per-task=8 --mem=12G --time=00:20:00 --output=logs/baseline-v2-%j.out --error=logs/baseline-v2-%j.err --wrap='../env/bin/python tools/run_baseline_v2.py'
