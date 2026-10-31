#!/bin/bash
#SBATCH --job-name=cow-photo-reference
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/causal_photo_20261030/logs/reference-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/causal_photo_20261030/logs/reference-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export PYTHONDONTWRITEBYTECODE=1
cd /share/home/renly/projects/idcoo_research_20261026/causal_photo_20261030
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/reference_encoder.py
