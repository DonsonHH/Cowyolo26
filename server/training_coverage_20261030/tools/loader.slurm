#!/bin/bash
#SBATCH --job-name=training-real-loader
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=6
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/training_coverage_20261030/logs/loader-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/training_coverage_20261030/logs/loader-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
cd /share/home/renly/projects/idcoo_research_20261026/training_coverage_20261030
../env/bin/python -B tools/audit_loader.py
