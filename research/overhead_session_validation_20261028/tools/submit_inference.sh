set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
ROOT="$PROJECT/overhead_session_validation_20261028"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
test -s "$ROOT/protocol/inference_v1.json"
test -s "$ROOT/results/admission/summary.json"
test -s "$ROOT/input/confirmation_counter.py"
sbatch --parsable --partition=4gpu --nodes=1 --ntasks=1 --gres=gpu:V100S:1 --cpus-per-task=4 --mem=12G --time=00:10:00 \
 --job-name=overhead-inference --output="$ROOT/logs/inference_%j.out" --error="$ROOT/logs/inference_%j.err" \
 --wrap="export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 HF_HUB_OFFLINE=1; $PROJECT/env/bin/python $ROOT/tools/infer_sessions.py"
