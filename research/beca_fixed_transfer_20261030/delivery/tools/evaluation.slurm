#!/bin/bash
#SBATCH --job-name=cow-beca-fixed20
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/beca_fixed_transfer_20261030/logs/evaluation-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/beca_fixed_transfer_20261030/logs/evaluation-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1
cd /share/home/renly/projects/idcoo_research_20261026/beca_fixed_transfer_20261030
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/evaluate_transfer.py
