set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
ROOT="$PROJECT/identity_source_provenance_20261029"
squeue -u renly -o '%.18i|%.9P|%.25j|%.8T|%.10M|%.10l|%R'
sbatch --parsable --partition=4gpu --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=8G --time=00:10:00 \
 --job-name=gallery-source-refine --output="$ROOT/logs/refine_%j.out" --error="$ROOT/logs/refine_%j.err" \
 --wrap="export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1; $PROJECT/env/bin/python $ROOT/tools/refine_geometry.py"
