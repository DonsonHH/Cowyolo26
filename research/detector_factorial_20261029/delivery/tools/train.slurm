#!/bin/bash
#SBATCH --job-name=cow-lowres-factorial
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=12G
#SBATCH --time=00:15:00
#SBATCH --array=0-14%3
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029/logs/train-%A_%a.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029/logs/train-%A_%a.err
set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
../env/bin/python tools/train_condition.py --condition-index "$SLURM_ARRAY_TASK_ID"
