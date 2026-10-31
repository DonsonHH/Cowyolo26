set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
ROOT="$PROJECT/overhead_long_session_20261028"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
test -s "$ROOT/next_probes_input.tar"
sbatch --parsable --partition=4gpu --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=3G --time=00:08:00 \
 --job-name=overhead-native-probes --output="$ROOT/logs/probes_%j.out" --error="$ROOT/logs/probes_%j.err" \
 --wrap="export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2; $PROJECT/env/bin/python $ROOT/tools/render_next_probes.py"
