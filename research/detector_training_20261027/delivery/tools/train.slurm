#!/usr/bin/env bash
#SBATCH --job-name=idcoo-detector-20x3
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:40:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/detector_training/logs/train-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/detector_training/logs/train-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 CUBLAS_WORKSPACE_CONFIG=:4096:8
export YOLO_OFFLINE=true YOLO_AUTOINSTALL=false WANDB_MODE=disabled COMET_MODE=DISABLED
export MPLCONFIGDIR=/share/home/renly/projects/idcoo_research_20261026/detector_training/cache/mpl
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/detector_training/tools/train_detector.py
