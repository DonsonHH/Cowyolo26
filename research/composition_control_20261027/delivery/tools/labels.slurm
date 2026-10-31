#!/usr/bin/env bash
#SBATCH --job-name=idcoo-composition-label-loader
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/composition_control/logs/labels-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/composition_control/logs/labels-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 YOLO_OFFLINE=true YOLO_AUTOINSTALL=false
export YOLO_CONFIG_DIR=/share/home/renly/projects/idcoo_research_20261026/composition_control/cache/labels/ultralytics
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/composition_control/tools/inspect_label_loading.py
