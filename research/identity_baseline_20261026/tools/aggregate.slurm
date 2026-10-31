#!/usr/bin/env bash
#SBATCH --job-name=idcoo-id-group-eval
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/identity_baseline/logs/aggregate-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/identity_baseline/logs/aggregate-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/identity_baseline/tools/aggregate_identity.py
