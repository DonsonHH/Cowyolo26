#!/usr/bin/env bash
#SBATCH --job-name=idcoo-qat-paired-study
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=00:25:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/qat_study/logs/study-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/qat_study/logs/study-%j.err
set -euo pipefail
export PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/deployment_audit/dependencies_offline
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=2 CUBLAS_WORKSPACE_CONFIG=:4096:8
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/qat_study/tools/train_qat.py
