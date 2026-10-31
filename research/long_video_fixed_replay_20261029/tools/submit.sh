set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
ROOT="$PROJECT/long_video_fixed_replay_20261029"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
test -s "$ROOT/protocol/replay_v1.json"
test -s "$ROOT/tools/replay.py"
mkdir -p "$ROOT/logs"
sbatch --parsable --partition=4gpu --nodes=1 --ntasks=1 --gres=gpu:V100S:1 --cpus-per-task=4 --mem=16G --time=00:20:00 \
 --job-name=long-video-fixed-replay --output="$ROOT/logs/replay_%j.out" --error="$ROOT/logs/replay_%j.err" \
 --wrap="export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 HF_HUB_OFFLINE=1; $PROJECT/env/bin/python $ROOT/tools/replay.py"
