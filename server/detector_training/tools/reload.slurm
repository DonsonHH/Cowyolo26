#!/usr/bin/env bash
#SBATCH --job-name=idcoo-detector-checkpoint-reload
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/detector_training/logs/reload-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/detector_training/logs/reload-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 YOLO_OFFLINE=true YOLO_AUTOINSTALL=false
export YOLO_CONFIG_DIR=/share/home/renly/projects/idcoo_research_20261026/detector_training/cache/reload
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/detector_training/tools/verify_checkpoints.py
