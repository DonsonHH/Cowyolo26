#!/usr/bin/env bash
#SBATCH --job-name=idcoo-reid-three-seeds
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=00:30:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/identity_training/logs/study-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/identity_training/logs/study-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/identity_training/tools/test_training_contract.py
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/identity_training/tools/smoke_train.py
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/identity_training/tools/train_and_evaluate.py
