#!/usr/bin/env bash
#SBATCH --job-name=idcoo-cows21-replay
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=00:20:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027/logs/infer-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027/logs/infer-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export YOLO_AUTOINSTALL=false
export YOLO_OFFLINE=true
export WANDB_MODE=disabled
export COMET_MODE=DISABLED
export YOLO_CONFIG_DIR=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027/cache/infer/ultralytics
export MPLCONFIGDIR=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027/cache/infer/mpl
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy
project=/share/home/renly/projects/idcoo_research_20261026
srun "$project/env/bin/python" "$project/cows2021_adaptation_20261027/tools/infer_fixed_models.py"
