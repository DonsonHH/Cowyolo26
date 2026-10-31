#!/bin/bash
#SBATCH --job-name=mosaic-pair-preflight
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=00:08:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030/logs/preflight-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030/logs/preflight-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
cd /share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030
../env/bin/python -B tools/preflight.py
