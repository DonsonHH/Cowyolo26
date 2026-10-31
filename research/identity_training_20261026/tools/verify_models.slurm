#!/usr/bin/env bash
#SBATCH --job-name=idcoo-reid-reload
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/identity_training/logs/reload-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/identity_training/logs/reload-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/identity_training/tools/verify_saved_models.py
