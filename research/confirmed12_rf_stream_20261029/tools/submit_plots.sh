set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
ROOT="$PROJECT/confirmed12_rf_stream_20261029"
squeue -u renly -o '%.18i|%.9P|%.25j|%.8T|%.10M|%.10l|%R'
sbatch --parsable --partition=cu --nodes=1 --ntasks=1 --cpus-per-task=1 --mem=2G --time=00:03:00 \
 --job-name=confirmed12-rf-plots --output="$ROOT/logs/plots_%j.out" --error="$ROOT/logs/plots_%j.err" \
 --wrap="export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1; $PROJECT/env/bin/python $ROOT/tools/render_plots.py"
