set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
cd /share/home/renly/projects/idcoo_research_20261026/crossdate_gallery_20261029
test ! -e results/study_v2
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sbatch --parsable --job-name=cow-crossdate-v2 --partition=4gpu --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=8G --time=00:10:00 --output=logs/study-v2-%j.out --error=logs/study-v2-%j.err --wrap='../env/bin/python tools/run_study_v2.py'
