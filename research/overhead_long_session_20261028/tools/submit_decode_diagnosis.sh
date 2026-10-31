set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
ROOT="$PROJECT/overhead_long_session_20261028"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
test -s "$ROOT/results/native_review/summary.json"
sbatch --parsable --partition=4gpu --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=2G --time=00:10:00 \
 --job-name=overhead-decode-diag --output="$ROOT/logs/decode_%j.out" --error="$ROOT/logs/decode_%j.err" \
 --wrap="export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2; $PROJECT/env/bin/python $ROOT/tools/diagnose_decode.py"
