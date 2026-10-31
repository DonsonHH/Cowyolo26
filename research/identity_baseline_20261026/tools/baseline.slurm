#!/usr/bin/env bash
#SBATCH --job-name=idcoo-id-features
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=00:15:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/identity_baseline/logs/baseline-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/identity_baseline/logs/baseline-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/identity_baseline/tools/test_identity_metrics.py
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/identity_baseline/tools/run_identity_baseline.py
