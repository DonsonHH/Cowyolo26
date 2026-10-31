#!/usr/bin/env bash
#SBATCH --job-name=cow-secondstage-media
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:08:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/secondstage_iou_20261028/logs/media-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/secondstage_iou_20261028/logs/media-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
cd /share/home/renly/projects/idcoo_research_20261026/secondstage_iou_20261028
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/render_media.py
