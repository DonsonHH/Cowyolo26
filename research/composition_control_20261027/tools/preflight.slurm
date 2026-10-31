#!/usr/bin/env bash
#SBATCH --job-name=idcoo-composition-preflight
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:08:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/composition_control/logs/preflight-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/composition_control/logs/preflight-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=2 CUBLAS_WORKSPACE_CONFIG=:4096:8
export YOLO_OFFLINE=true YOLO_AUTOINSTALL=false
export YOLO_CONFIG_DIR=/share/home/renly/projects/idcoo_research_20261026/composition_control/cache/ultralytics
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/composition_control/tools/preflight.py
