#!/bin/bash
#SBATCH --job-name=recover-loader-records
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=3G
#SBATCH --time=00:03:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/training_coverage_20261030/logs/recover-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/training_coverage_20261030/logs/recover-%j.err
set -euo pipefail
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
cd /share/home/renly/projects/idcoo_research_20261026/training_coverage_20261030
../env/bin/python -B tools/recover_loader.py
