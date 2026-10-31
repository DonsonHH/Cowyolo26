set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
ROOT="$PROJECT/long_video_track_gap_20261029"
squeue -u renly -o '%.18i|%.9P|%.25j|%.8T|%.10M|%.10l|%R'
sbatch --parsable --partition=cu --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=4G --time=00:05:00 \
 --job-name=long-firststage-control --output="$ROOT/logs/control_%j.out" --error="$ROOT/logs/control_%j.err" \
 --wrap="export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 HF_HUB_OFFLINE=1; $PROJECT/env/bin/python $ROOT/tools/firststage_control.py"
