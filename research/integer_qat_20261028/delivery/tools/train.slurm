#!/usr/bin/env bash
#SBATCH --job-name=idcoo-int-QAT-paired
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=14G
#SBATCH --time=00:30:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/integer_qat_20261028/logs/train-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/integer_qat_20261028/logs/train-%j.err
set -euo pipefail
export PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/deployment_audit/dependencies_offline
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 CUBLAS_WORKSPACE_CONFIG=:4096:8
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
cd /share/home/renly/projects/idcoo_research_20261026/integer_qat_20261028
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/train.py
