#!/usr/bin/env bash
#SBATCH --job-name=idcoo-range-check
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/activation_range_20261028/logs/verify-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/activation_range_20261028/logs/verify-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
cd /share/home/renly/projects/idcoo_research_20261026/activation_range_20261028
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/independent_verify.py
