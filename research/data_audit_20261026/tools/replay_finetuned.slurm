#!/usr/bin/env bash
#SBATCH --job-name=idcoo-pilot-replay
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=00:15:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/logs/pilot-replay-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/logs/pilot-replay-%j.err
set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export YOLO_OFFLINE=true
export YOLO_CONFIG_DIR="$ROOT/yolo_settings"
export IDCOO_MODEL_PATH="$ROOT/results/detection_pilot/five_epoch_dev/weights/best.pt"
export IDCOO_COUNT_OUTPUT=counting_finetuned_dev
export IDCOO_MC_OUTPUT=multicam_count_finetuned_dev
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy
srun "$ROOT/env/bin/python" "$ROOT/tools/counting_baseline.py"
srun "$ROOT/env/bin/python" "$ROOT/tools/counting_multicam_dev.py"
