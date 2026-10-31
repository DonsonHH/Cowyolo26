set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
ROOT="$PROJECT/overhead_positive_reference_20261028"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
test -s "$ROOT/input/2023-08-17T13-25-38.mp4"
test -s "$ROOT/input/video_manifest.json"
mkdir -p "$ROOT/logs"
sbatch --parsable --partition=4gpu --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=4G --time=00:15:00 \
 --job-name=overhead-positive-native --output="$ROOT/logs/admission_%j.out" --error="$ROOT/logs/admission_%j.err" \
 --wrap="export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2; set -e; $PROJECT/env/bin/python $ROOT/tools/prepare_native_review.py; $PROJECT/env/bin/python $ROOT/tools/diagnose_decode.py"
