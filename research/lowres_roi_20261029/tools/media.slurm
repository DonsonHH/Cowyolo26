#!/bin/bash
#SBATCH --job-name=cow-roi-media
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=6G
#SBATCH --time=00:06:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/lowres_roi_20261029/logs/media-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/lowres_roi_20261029/logs/media-%j.err
set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/lowres_roi_20261029
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
../env/bin/python tools/render_media.py
