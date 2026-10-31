#!/usr/bin/env bash
#SBATCH --job-name=cow-count-recovery
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=00:35:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028/logs/replay-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028/logs/replay-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
export YOLO_OFFLINE=true HF_HUB_OFFLINE=1
cd /share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/replay.py
