set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
ROOT="$PROJECT/overhead_long_session_20261028"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
test -s "$ROOT/input/video_manifest.json"
test -s "$ROOT/input/2023-08-17T12-54-41.mp4"
mkdir -p "$ROOT/logs"
# cu is fully allocated in the fresh snapshot; two CPU cores only, no GPU requested.
sbatch --parsable --partition=4gpu --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=4G --time=00:15:00 \
 --job-name=overhead-long-native --output="$ROOT/logs/native_%j.out" --error="$ROOT/logs/native_%j.err" \
 --wrap="export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2; $PROJECT/env/bin/python $ROOT/tools/prepare_native_review.py"
