set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
ROOT="$PROJECT/overhead_positive_reference_20261028"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
test -s "$ROOT/protocol/focused_review_v1.json"
test -s "$ROOT/results/native_review/summary.json"
sbatch --parsable --partition=4gpu --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=4G --time=00:10:00 \
 --job-name=overhead-reference-focus --output="$ROOT/logs/focused_%j.out" --error="$ROOT/logs/focused_%j.err" \
 --wrap="export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2; $PROJECT/env/bin/python $ROOT/tools/render_focused.py"
