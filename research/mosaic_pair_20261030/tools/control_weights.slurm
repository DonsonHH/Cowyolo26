#!/bin/bash
#SBATCH --job-name=mosaic-control-weights
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=6G
#SBATCH --time=00:03:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030/logs/control-weights-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030/logs/control-weights-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
cd /share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030
../env/bin/python -B tools/audit_control_weights.py
