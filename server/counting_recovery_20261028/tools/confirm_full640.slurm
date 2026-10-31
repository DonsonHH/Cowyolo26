#!/usr/bin/env bash
#SBATCH --job-name=cow-count-full640-seeds
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=00:15:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028/logs/full640-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028/logs/full640-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
cd /share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/confirm_full640.py
