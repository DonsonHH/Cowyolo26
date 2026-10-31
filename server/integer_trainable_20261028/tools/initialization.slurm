#!/usr/bin/env bash
#SBATCH --job-name=idcoo-int-init-check
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/integer_trainable_20261028/logs/initialization-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/integer_trainable_20261028/logs/initialization-%j.err
set -euo pipefail
export PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/deployment_audit/dependencies_offline
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
cd /share/home/renly/projects/idcoo_research_20261026/integer_trainable_20261028
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/initialization_probe.py
