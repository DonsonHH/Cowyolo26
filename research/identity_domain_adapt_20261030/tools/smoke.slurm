#!/bin/bash
#SBATCH --job-name=cow-id-domain-smoke
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/identity_domain_adapt_20261030/logs/smoke-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/identity_domain_adapt_20261030/logs/smoke-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export PYTHONDONTWRITEBYTECODE=1
cd /share/home/renly/projects/idcoo_research_20261026/identity_domain_adapt_20261030
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/smoke.py
