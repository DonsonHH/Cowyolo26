#!/bin/bash
#SBATCH --job-name=cow-id-domain-pair
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --array=0-5%2
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/identity_domain_adapt_20261030/logs/train-%A_%a.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/identity_domain_adapt_20261030/logs/train-%A_%a.err
set -euo pipefail
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export PYTHONDONTWRITEBYTECODE=1
cd /share/home/renly/projects/idcoo_research_20261026/identity_domain_adapt_20261030
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/train_condition.py --index "$SLURM_ARRAY_TASK_ID"
