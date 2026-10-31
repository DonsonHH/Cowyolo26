set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
ROOT="$PROJECT/overhead_session_validation_20261028"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
test -s "$ROOT/evidence/fetch_manifest.json"
test -s "$ROOT/tools/audit_videos.py"
mkdir -p "$ROOT/logs"
# Live cu partition is fully allocated; use two CPU cores on idle 4gpu, no GPU GRES.
sbatch --parsable --partition=4gpu --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=4G --time=00:10:00 \
 --job-name=overhead-admission --output="$ROOT/logs/admission_%j.out" --error="$ROOT/logs/admission_%j.err" \
 --wrap="export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2; $PROJECT/env/bin/python $ROOT/tools/audit_videos.py"
