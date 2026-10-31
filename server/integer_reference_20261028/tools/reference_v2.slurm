#!/usr/bin/env bash
#SBATCH --job-name=idcoo-intref-v2
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:20:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028/logs/reference-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028/logs/reference-%j.err
set -euo pipefail
export PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/deployment_audit/dependencies_offline
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export MKL_NUM_THREADS=2
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
cd /share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/run_reference.py
