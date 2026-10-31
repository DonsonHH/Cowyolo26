#!/usr/bin/env bash
#SBATCH --job-name=idcoo-detector-source-compare
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=00:15:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/detector_training/logs/infer-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/detector_training/logs/infer-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 CUBLAS_WORKSPACE_CONFIG=:4096:8
export YOLO_OFFLINE=true YOLO_AUTOINSTALL=false WANDB_MODE=disabled COMET_MODE=DISABLED
export YOLO_CONFIG_DIR=/share/home/renly/projects/idcoo_research_20261026/detector_training/cache/ultralytics
export MPLCONFIGDIR=/share/home/renly/projects/idcoo_research_20261026/detector_training/cache/mpl
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/detector_training/tools/infer_fixed_models.py
