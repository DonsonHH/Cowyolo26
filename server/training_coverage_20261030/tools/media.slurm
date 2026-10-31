#!/bin/bash
#SBATCH --job-name=train-coverage-media
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=00:04:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/training_coverage_20261030/logs/media-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/training_coverage_20261030/logs/media-%j.err
set -euo pipefail
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
cd /share/home/renly/projects/idcoo_research_20261026/training_coverage_20261030
../env/bin/python -B tools/render_media.py
