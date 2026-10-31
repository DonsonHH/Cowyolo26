set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
ROOT="$PROJECT/identity_source_provenance_20261029"
squeue -u renly -o '%.18i|%.9P|%.25j|%.8T|%.10M|%.10l|%R'
sbatch --parsable --partition=4gpu --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=4G --time=00:03:00 \
 --job-name=gallery-source-endpoints --output="$ROOT/logs/endpoint_%j.out" --error="$ROOT/logs/endpoint_%j.err" \
 --wrap="export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1; $PROJECT/env/bin/python $ROOT/tools/check_endpoints.py"
