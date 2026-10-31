set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
ROOT="$PROJECT/firststage_iou_regression_20261029"
squeue -u renly -o '%.18i|%.9P|%.25j|%.8T|%.10M|%.10l|%R'
mkdir -p "$ROOT/logs"
sbatch --parsable --partition=cu --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=8G --time=00:10:00 \
 --job-name=firststage-iou-regression --output="$ROOT/logs/regression_%j.out" --error="$ROOT/logs/regression_%j.err" \
 --wrap="export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 HF_HUB_OFFLINE=1; $PROJECT/env/bin/python $ROOT/tools/replay.py"
