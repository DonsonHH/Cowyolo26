#!/bin/bash
#SBATCH --job-name=mosaic-oldtrace-probe
#SBATCH --partition=4gpu
#SBATCH --nodelist=gpu02
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=00:03:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030/logs/regression-probe-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030/logs/regression-probe-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
cd /share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030
../env/bin/python -B tools/probe_regression.py
