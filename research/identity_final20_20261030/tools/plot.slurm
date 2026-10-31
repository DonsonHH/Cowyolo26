#!/bin/bash
#SBATCH --job-name=cow-final20-figure
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:03:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/identity_final20_20261030/logs/figure-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/identity_final20_20261030/logs/figure-%j.err
set -euo pipefail
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd /share/home/renly/projects/idcoo_research_20261026/identity_final20_20261030
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/plot_primary.py
