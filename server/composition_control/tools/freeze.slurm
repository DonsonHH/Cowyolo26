#!/usr/bin/env bash
#SBATCH --job-name=idcoo-composition-freeze
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/composition_control/logs/freeze-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/composition_control/logs/freeze-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 YOLO_AUTOINSTALL=false YOLO_OFFLINE=true
export YOLO_CONFIG_DIR=/share/home/renly/projects/idcoo_research_20261026/composition_control/cache/freeze/ultralytics
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/composition_control/tools/freeze_models.py
