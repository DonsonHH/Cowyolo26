#!/bin/bash
#SBATCH --job-name=mosaic-pair-train
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=24G
#SBATCH --time=00:30:00
#SBATCH --array=0-5%3
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030/logs/train-%A_%a.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030/logs/train-%A_%a.err
set -euo pipefail
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
cd /share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030
../env/bin/python -B tools/train_condition.py --condition-index "$SLURM_ARRAY_TASK_ID"
