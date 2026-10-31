#!/bin/bash
#SBATCH --job-name=unconfirmed-stage-IoU
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=6G
#SBATCH --time=00:10:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/unconfirmed_iou_20261030/logs/control-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/unconfirmed_iou_20261030/logs/control-%j.err
set -euo pipefail
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
cd /share/home/renly/projects/idcoo_research_20261026/unconfirmed_iou_20261030
../env/bin/python -B tools/run_control.py
